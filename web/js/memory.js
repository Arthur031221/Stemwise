// What the studio remembers between visits: the practice setup of each song, and a few global preferences.

const SONG = "stemwise.song.";
const PREFS = "stemwise.prefs";
const LAST = "stemwise.last";

const clamp = (v, lo, hi, fallback) => (Number.isFinite(Number(v)) && v !== null && v !== "" ? Math.min(hi, Math.max(lo, Number(v))) : fallback);

/** The part of the studio state worth keeping for one song. */
export function packSong(s) {
  return {
    tempo: s.tempo,
    pitch: s.pitch,
    gains: Object.fromEntries(s.gains),
    muted: [...s.muted],
    solo: [...s.solo],
    loop: s.loop ? { start: s.loop.start, end: s.loop.end, on: s.loopOn } : null,
  };
}

/** Turn whatever is in storage into a safe patch for this song. Anything unusable is left out. */
export function unpackSong(raw, stems, duration) {
  const out = {};
  if (!raw || typeof raw !== "object") return out;
  if (raw.tempo !== undefined) out.tempo = Math.round(clamp(raw.tempo, 25, 150, 100));
  if (raw.pitch !== undefined) out.pitch = Math.round(clamp(raw.pitch, -6, 6, 0));
  if (raw.gains && typeof raw.gains === "object") {
    out.gains = Object.fromEntries(stems.map((n) => [n, clamp(raw.gains[n], 0, 1.2, 1)]));
  }
  for (const key of ["muted", "solo"]) {
    if (Array.isArray(raw[key])) out[key] = raw[key].filter((n) => stems.includes(n));
  }
  const l = raw.loop;
  if (l && typeof l === "object") {
    const start = Number(l.start);
    const end = Number(l.end);
    if (Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end > start && end <= duration + 0.5) {
      out.loop = { start, end, on: l.on !== false };
    }
  }
  return out;
}

export function packPrefs(s) {
  return { click: s.click, clickGain: s.clickGain, countIn: s.countIn, flats: s.flats };
}

export function unpackPrefs(raw) {
  const out = {};
  if (!raw || typeof raw !== "object") return out;
  for (const key of ["click", "countIn", "flats"]) if (typeof raw[key] === "boolean") out[key] = raw[key];
  if (raw.clickGain !== undefined) out.clickGain = clamp(raw.clickGain, 0, 1, 0.6);
  return out;
}

function read(storage, key) {
  try {
    return JSON.parse(storage.getItem(key));
  } catch {
    return null;
  }
}

function write(storage, key, value) {
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage can be full or blocked in private windows. Practice goes on without it.
  }
}

export const memory = {
  song: (storage, id) => read(storage, SONG + id),
  saveSong: (storage, id, data) => write(storage, SONG + id, data),
  forget: (storage, id) => { try { storage.removeItem(SONG + id); } catch { /* nothing to forget */ } },
  prefs: (storage) => read(storage, PREFS),
  savePrefs: (storage, data) => write(storage, PREFS, data),
  last: (storage) => { try { return storage.getItem(LAST); } catch { return null; } },
  saveLast: (storage, id) => { try { storage.setItem(LAST, id); } catch { /* ignore */ } },
};

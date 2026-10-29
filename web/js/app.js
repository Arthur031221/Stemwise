import { Api, STEMS } from "./api.js";
import { Player } from "./player.js";
import { Timeline, HEAD_H, LANE_H, PEAKS_PER_SECOND } from "./timeline.js";
import { computePeaks, barIndexAt, resizeLoop } from "./peaks.js";
import { parseChord, transposeKey, transposeLabel } from "./chords.js";
import { guitarSvg, pianoSvg } from "./diagrams.js";
import { Trainer } from "./trainer.js";
import { memory, packSong, unpackSong, packPrefs, unpackPrefs } from "./memory.js";
import { LOCALES, initLocale, setLocale, locale, t } from "./i18n.js";

const $ = (id) => document.getElementById(id);
const api = new Api();
const player = new Player();
const trainer = new Trainer();

const state = {
  song: null,
  gains: new Map(STEMS.map((s) => [s, 1])),
  muted: new Set(),
  solo: new Set(),
  tempo: 100,
  pitch: 0,
  loop: null,
  loopOn: false,
  click: false,
  clickGain: 0.6,
  countIn: false,
  flats: false,
  trainerOn: false,
  anchor: { sample: 0, stamp: 0 },
  shownChord: null,
  poll: 0,
};

let timeline;

// ---------- memory ----------

/** Keep the setup of the open song and the global preferences, so a reload picks up where practice stopped. */
function remember() {
  if (!state.song) return;
  memory.saveSong(localStorage, state.song.id, packSong(state));
  memory.savePrefs(localStorage, packPrefs(state));
}

// ---------- helpers ----------

function toast(message, error = false) {
  const box = $("toast");
  box.textContent = message;
  box.className = error ? "toast error" : "toast";
  box.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { box.hidden = true; }, error ? 6000 : 2600);
}

function show(view) {
  for (const id of ["empty", "processing", "studio"]) $(id).hidden = id !== view;
  document.body.dataset.view = view;
}

const clock = (s) => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, "0")}`;
const stemLabel = (name) => t(`stem.${name}`);

// ---------- songs ----------

async function refreshSongs(select = null) {
  const songs = await api.songs();
  const box = $("song-select");
  box.replaceChildren();
  for (const s of songs) {
    const opt = new Option(s.status === "ready" ? s.title : `${s.title} (${t(`stage.${s.stage}`)})`, s.id);
    box.add(opt);
  }
  box.hidden = songs.length === 0;
  if (select) box.value = select;
  return songs;
}

async function openSong(id) {
  clearTimeout(state.poll);
  const meta = await api.song(id);
  $("song-select").value = id;
  if (meta.status === "ready") return loadSong(meta);
  if (meta.status === "error") {
    show("empty");
    toast(t("error.processing", { reason: meta.error || "" }), true);
    return null;
  }
  showProcessing(meta);
  state.poll = setTimeout(() => openSong(id).catch(report), 1000);
  return null;
}

function showProcessing(meta) {
  show("processing");
  $("proc-title").textContent = t("proc.title", { name: meta.title });
  $("proc-bar").style.width = `${Math.round((meta.progress || 0) * 100)}%`;
  $("proc-stage").textContent = t(`stage.${meta.stage}`);
  document.querySelector(".progress").setAttribute("aria-valuenow", Math.round((meta.progress || 0) * 100));
}

async function loadSong(meta) {
  show("processing");
  $("proc-title").textContent = t("proc.loading", { name: meta.title });
  $("proc-bar").style.width = "10%";
  $("proc-stage").textContent = "";
  player.pause();
  await player.init();

  const buffers = [];
  for (const [i, stem] of STEMS.entries()) {
    const res = await fetch(api.stemUrl(meta.id, stem));
    if (!res.ok) throw new Error(`${stem}: ${res.status}`);
    buffers.push(await player.ctx.decodeAudioData(await res.arrayBuffer()));
    $("proc-bar").style.width = `${10 + ((i + 1) / STEMS.length) * 80}%`;
  }
  await player.load(buffers);

  const bins = Math.ceil(meta.duration * PEAKS_PER_SECOND);
  const stems = STEMS.map((name, i) => ({
    name,
    peaks: computePeaks(buffers[i].getChannelData(0), buffers[i].getChannelData(Math.min(1, buffers[i].numberOfChannels - 1)), bins),
  }));

  state.song = meta;
  state.muted.clear();
  state.solo.clear();
  state.gains = new Map(STEMS.map((s) => [s, 1]));
  state.loop = null;
  state.loopOn = false;
  state.shownChord = null;
  const saved = unpackSong(memory.song(localStorage, meta.id), STEMS, meta.duration);
  state.tempo = saved.tempo ?? 100;
  state.pitch = saved.pitch ?? 0;
  if (saved.gains) state.gains = new Map(Object.entries(saved.gains));
  for (const name of saved.muted ?? []) state.muted.add(name);
  for (const name of saved.solo ?? []) state.solo.add(name);
  if (saved.loop) {
    state.loop = { start: saved.loop.start, end: saved.loop.end };
    state.loopOn = saved.loop.on;
  }
  memory.saveLast(localStorage, meta.id);
  trainer.reset();
  setTrainer(false);

  show("studio");
  buildStrips();
  timeline.setSong(meta, stems);
  applyTimelineMetrics();
  $("song-title").textContent = meta.title;
  showKey();
  $("chip-bpm").textContent = `${Math.round(meta.bpm)} BPM`;
  const demo = api.mode === "demo";
  $("chip-demo").hidden = !demo;
  $("chip-demo").textContent = t("demo.chip");
  $("export-btn").hidden = demo;
  renderCredit(meta);
  pushAll();
  setPitch(state.pitch);
  if (state.loop) player.seek(state.loop.start);
  updateLoopUi();
  tick();
  return meta;
}

function renderCredit(meta) {
  const box = $("credit");
  box.hidden = !meta.credit;
  if (!meta.credit) return;
  const c = meta.credit;
  box.replaceChildren(t("credit.prefix") + " ");
  const a = document.createElement("a");
  a.href = c.url;
  a.textContent = `${c.title} by ${c.artist}`;
  a.rel = "noopener";
  box.append(a, ` (${c.license}). ${t("credit.suffix")}`);
}

function applyTimelineMetrics() {
  const root = document.documentElement.style;
  root.setProperty("--head-h", `${HEAD_H}px`);
  root.setProperty("--lane-h", `${LANE_H}px`);
}

function buildStrips() {
  const box = $("strips");
  box.replaceChildren();
  for (const name of STEMS) {
    const strip = document.createElement("div");
    strip.className = "strip";
    strip.dataset.stem = name;
    strip.style.setProperty("--stem-color", `var(--c-${name})`);
    strip.innerHTML = `<span class="name"></span><button class="sm m" aria-pressed="false" title="M">M</button><button class="sm s" aria-pressed="false" title="S">S</button><input type="range" min="0" max="1.2" step="0.01" value="1">`;
    strip.querySelector(".name").textContent = stemLabel(name);
    const [mute, solo] = strip.querySelectorAll("button");
    mute.setAttribute("aria-label", `${stemLabel(name)}: ${t("strip.mute")}`);
    solo.setAttribute("aria-label", `${stemLabel(name)}: ${t("strip.solo")}`);
    mute.onclick = () => toggleSet(state.muted, name);
    solo.onclick = () => toggleSet(state.solo, name);
    strip.querySelector("input").value = state.gains.get(name);
    strip.querySelector("input").oninput = (e) => { state.gains.set(name, Number(e.target.value)); pushGains(); };
    box.append(strip);
  }
}

function toggleSet(set, name) {
  if (set.has(name)) set.delete(name);
  else set.add(name);
  pushGains();
}

function effectiveGain(name) {
  if (state.solo.size) return state.solo.has(name) ? state.gains.get(name) : 0;
  return state.muted.has(name) ? 0 : state.gains.get(name);
}

function pushGains() {
  const gains = STEMS.map(effectiveGain);
  player.setGains(gains);
  remember();
  const silent = new Set(STEMS.filter((_, i) => gains[i] === 0));
  timeline.setMuted(silent);
  for (const strip of $("strips").children) {
    const name = strip.dataset.stem;
    const [mute, solo] = strip.querySelectorAll("button");
    mute.setAttribute("aria-pressed", String(state.muted.has(name)));
    solo.setAttribute("aria-pressed", String(state.solo.has(name)));
    strip.classList.toggle("dim", silent.has(name));
  }
}

// ---------- engine state ----------

function pushAll() {
  pushGains();
  setTempo(state.tempo, false);
  player.setPitch(state.pitch);
  player.setVolume(Number($("master").value));
  pushClick();
  pushLoop();
}

function setTempo(percent, fromUser = true) {
  state.tempo = Math.min(150, Math.max(25, Math.round(percent)));
  player.setTempo(state.tempo / 100);
  $("tempo").value = state.tempo;
  $("tempo-out").textContent = `${state.tempo}%`;
  for (const b of $("tempo-presets").children) b.classList.toggle("on", Number(b.dataset.value) === state.tempo);
  if (fromUser && state.trainerOn) trainer.reset();
  state.anchor = { sample: player.sample, stamp: performance.now() };
  remember();
}

function showKey() {
  if (state.song) $("chip-key").textContent = transposeKey(state.song.key, state.pitch, state.flats);
}

function setPitch(semitones) {
  state.pitch = Math.min(6, Math.max(-6, Math.round(semitones)));
  player.setPitch(state.pitch);
  $("pitch").value = state.pitch;
  $("pitch-out").textContent = state.pitch > 0 ? `+${state.pitch}` : String(state.pitch);
  state.shownChord = null;
  showKey();
  timeline.setLabelFn(chordLabel);
  tick();
  remember();
}

function pushClick() {
  const song = state.song;
  if (!song) return;
  player.setClick(state.click, song.beats, song.downbeats, state.clickGain);
  remember();
}

function pushLoop() {
  if (state.loop) player.setLoop(state.loop.start, state.loop.end, state.loopOn);
  else player.setLoop(0, 0, false);
  timeline.setLoop(state.loopOn || state.loop ? state.loop : null);
  remember();
}

function setLoop(range) {
  state.loop = range;
  state.loopOn = !!range;
  if (range && (player.time < range.start || player.time >= range.end)) player.seek(range.start);
  pushLoop();
  updateLoopUi();
}

function updateLoopUi() {
  const has = !!state.loop;
  $("loop-toggle").setAttribute("aria-pressed", String(state.loopOn));
  $("loop-clear").hidden = !has;
  if (has && state.song) {
    const from = barIndexAt(state.song.downbeats, state.loop.start + 0.01) + 1;
    const to = barIndexAt(state.song.downbeats, state.loop.end - 0.01) + 1;
    $("loop-info").textContent = t("loop.range", { from, to });
  } else {
    $("loop-info").textContent = t("loop.hint");
  }
}

function chordLabel(label) {
  return transposeLabel(label, state.pitch, state.flats);
}

// ---------- trainer ----------

function readTrainerFields() {
  trainer.configure({
    start: $("tr-start").value, step: $("tr-step").value, goal: $("tr-goal").value, loops: $("tr-loops").value,
  });
}

function setTrainer(on) {
  state.trainerOn = on;
  $("trainer-toggle").setAttribute("aria-pressed", String(on));
  $("trainer-toggle").textContent = t(on ? "trainer.running" : "trainer.off");
  $("tr-miss").hidden = !on;
  if (on) {
    readTrainerFields();
    setTempo(trainer.tempo, false);
  }
  trainerStatus();
}

function trainerStatus() {
  const box = $("tr-status");
  if (!state.trainerOn) { box.textContent = ""; return; }
  box.textContent = trainer.done
    ? t("trainer.done", { tempo: trainer.tempo })
    : t("trainer.status", { tempo: trainer.tempo, clean: trainer.clean, loops: trainer.loops });
}

function onLooped() {
  if (!state.trainerOn || !state.loopOn) return;
  if (trainer.loopFinished()) {
    setTempo(trainer.tempo, false);
    toast(t("trainer.faster", { tempo: trainer.tempo }));
  }
  trainerStatus();
}

// ---------- transport ----------

async function togglePlay() {
  if (!state.song) return;
  if (player.playing) { player.pause(); updatePlayIcon(); return; }
  if (state.countIn && state.click) await countIn();
  await player.play();
  state.anchor = { sample: player.sample, stamp: performance.now() };
  updatePlayIcon();
}

function updatePlayIcon() {
  $("icon-play").hidden = player.playing;
  $("icon-pause").hidden = !player.playing;
  $("play").setAttribute("aria-label", t(player.playing ? "transport.pause" : "transport.play"));
}

async function countIn() {
  const song = state.song;
  const perBar = Math.max(1, Math.round(song.beats.length / Math.max(1, song.downbeats.length)));
  const gap = 60 / song.bpm / (state.tempo / 100);
  await player.ctx.resume();
  const start = player.ctx.currentTime + 0.05;
  for (let i = 0; i < perBar; i++) {
    const osc = player.ctx.createOscillator();
    const gain = player.ctx.createGain();
    osc.frequency.value = i === 0 ? 1500 : 1000;
    const at = start + i * gap;
    gain.gain.setValueAtTime(state.clickGain * 0.6, at);
    gain.gain.exponentialRampToValueAtTime(0.001, at + 0.06);
    osc.connect(gain).connect(player.ctx.destination);
    osc.start(at);
    osc.stop(at + 0.07);
  }
  await new Promise((resolve) => setTimeout(resolve, (perBar * gap + 0.05) * 1000));
}

/** The bar the playhead is in, as a loop range, or null when the song has no beat grid. */
function barAtPlayhead() {
  const d = state.song?.downbeats;
  if (!d || d.length < 2) return null;
  const i = Math.max(0, barIndexAt(d, player.time + 0.05));
  return { start: d[i], end: d[i + 1] ?? state.song.duration };
}

/** Shift with an arrow: make the loop one bar longer or shorter. With no loop yet, Shift+Right starts one on this bar. */
function resizeLoopBy(delta) {
  if (!state.loop) {
    const bar = delta > 0 ? barAtPlayhead() : null;
    if (bar) setLoop(bar);
    return;
  }
  const next = resizeLoop(state.song.downbeats, state.song.duration, state.loop, delta);
  setLoop(next);
  if (player.time < next.start || player.time >= next.end) player.seek(next.start);
}

function seekRelativeBars(delta) {
  const d = state.song.downbeats;
  const cur = Math.max(0, barIndexAt(d, player.time + 0.05));
  // Left inside a bar goes back to its start first, and only from the start goes to the previous bar.
  const target = delta < 0 && player.time - d[cur] > 0.25 ? cur + delta + 1 : cur + delta;
  player.seek(d[Math.max(0, Math.min(d.length - 1, target))] ?? 0);
}

// ---------- per-frame ----------

/** The worklet reports its position every ~46 ms, so the playhead is advanced locally in between. */
function currentTime() {
  if (!player.playing) return player.time;
  const elapsed = ((performance.now() - state.anchor.stamp) / 1000) * (state.tempo / 100);
  let time = player.time + Math.min(0.06, elapsed);
  if (state.loopOn && state.loop) time = Math.min(time, state.loop.end);
  return Math.min(time, player.duration);
}

function tick() {
  const song = state.song;
  if (!song) return;
  const time = currentTime();
  $("clock-time").textContent = clock(time);
  const bar = barIndexAt(song.downbeats, time) + 1;
  $("clock-bar").textContent = bar > 0 ? t("clock.bar", { n: bar, total: song.downbeats.length }) : "";
  timeline.setTime(time);
  updateChord(time);
}

function updateChord(time) {
  const chords = state.song.chords;
  const idx = chords.findIndex((c) => time >= c.start && time < c.end);
  const key = `${idx}|${state.pitch}|${state.flats}`;
  if (key === state.shownChord) return;
  state.shownChord = key;
  const now = chords[idx];
  let next = null;
  for (let i = idx + 1; i < chords.length && idx >= 0; i++) {
    if (chords[i].label !== "N" && chords[i].label !== now?.label) { next = chords[i]; break; }
  }
  const name = (c) => (c && c.label !== "N" ? chordLabel(c.label) : "-");
  $("chord-now").textContent = name(now);
  $("chord-next").textContent = name(next);
  const parsed = now && now.label !== "N" ? parseChord(transposeLabel(now.label, state.pitch, false)) : null;
  $("guitar-diagram").replaceChildren(guitarSvg(parsed));
  $("piano-diagram").replaceChildren(pianoSvg(parsed));
}

function frame() {
  if (player.playing) tick();
  requestAnimationFrame(frame);
}

// ---------- export ----------

function buildExportMenu() {
  const menu = $("export-menu");
  menu.replaceChildren();
  const id = state.song.id;
  const silent = STEMS.filter((s) => effectiveGain(s) === 0);
  const items = [
    [t("export.backing"), api.exportUrl(id, "backing", silent.length ? `?without=${silent.join(",")}` : "")],
    [t("export.stems"), api.exportUrl(id, "stems")],
    [t("export.chords_txt"), api.exportUrl(id, "chords.txt")],
    [t("export.chords_html"), api.exportUrl(id, "chords.html")],
    [t("export.beats"), api.exportUrl(id, "beats.mid")],
  ];
  for (const [label, href] of items) {
    const a = document.createElement("a");
    a.textContent = label;
    a.href = href;
    a.setAttribute("role", "menuitem");
    a.download = "";
    menu.append(a);
  }
  const del = document.createElement("button");
  del.textContent = t("export.delete");
  del.setAttribute("role", "menuitem");
  del.onclick = async () => {
    if (!confirm(t("export.confirm_delete", { name: state.song.title }))) return;
    player.pause();
    await api.remove(id);
    memory.forget(localStorage, id);
    state.song = null;
    await afterSongsChanged();
  };
  menu.append(del);
}

function toggleMenu(open) {
  const menu = $("export-menu");
  if (open) buildExportMenu();
  menu.hidden = !open;
  $("export-btn").setAttribute("aria-expanded", String(open));
}

// ---------- uploads ----------

async function upload(file) {
  if (api.mode !== "server") { toast(t("demo.noupload"), true); return; }
  try {
    show("processing");
    $("proc-title").textContent = t("proc.uploading", { name: file.name });
    $("proc-bar").style.width = "2%";
    $("proc-stage").textContent = "";
    const result = await api.upload(file, (f) => { $("proc-bar").style.width = `${Math.round(f * 100)}%`; });
    await refreshSongs(result.id);
    await openSong(result.id);
  } catch (err) {
    report(err);
    await afterSongsChanged();
  }
}

async function afterSongsChanged() {
  const songs = await refreshSongs();
  if (songs.length) await openSong(songs[0].id);
  else show("empty");
}

function report(err) {
  console.error(err);
  toast(String(err.message || err), true);
}

// ---------- wiring ----------

function wire() {
  $("play").onclick = () => togglePlay().catch(report);
  $("restart").onclick = () => player.seek(state.loop && state.loopOn ? state.loop.start : 0);
  $("tempo").oninput = (e) => setTempo(Number(e.target.value));
  $("pitch").oninput = (e) => setPitch(Number(e.target.value));
  $("master").oninput = (e) => player.setVolume(Number(e.target.value));
  for (const v of [50, 60, 70, 80, 90, 100]) {
    const b = document.createElement("button");
    b.textContent = `${v}%`;
    b.dataset.value = v;
    b.onclick = () => setTempo(v);
    $("tempo-presets").append(b);
  }
  $("loop-toggle").onclick = () => {
    if (!state.loop) {
      const bar = barAtPlayhead();
      if (bar) setLoop(bar); else toast(t("loop.hint"));
      return;
    }
    state.loopOn = !state.loopOn;
    pushLoop();
    updateLoopUi();
  };
  $("loop-clear").onclick = () => { setLoop(null); if (state.trainerOn) setTrainer(false); };
  $("click-toggle").onclick = () => {
    state.click = !state.click;
    $("click-toggle").setAttribute("aria-pressed", String(state.click));
    pushClick();
  };
  $("click-volume").oninput = (e) => { state.clickGain = Number(e.target.value); pushClick(); };
  $("count-in").onclick = () => {
    state.countIn = !state.countIn;
    $("count-in").setAttribute("aria-pressed", String(state.countIn));
    remember();
  };
  $("flats").onchange = (e) => { state.flats = e.target.checked; state.shownChord = null; showKey(); timeline.setLabelFn(chordLabel); tick(); remember(); };
  $("zoom-in").onclick = () => timeline.zoom(1.5);
  $("zoom-out").onclick = () => timeline.zoom(1 / 1.5);

  $("trainer-toggle").onclick = () => {
    if (!state.trainerOn && !state.loop) { toast(t("trainer.needs_loop"), true); return; }
    setTrainer(!state.trainerOn);
  };
  for (const id of ["tr-start", "tr-step", "tr-goal", "tr-loops"]) {
    $(id).onchange = () => { if (state.trainerOn) { readTrainerFields(); setTempo(trainer.tempo, false); trainerStatus(); } };
  }
  $("tr-miss").onclick = () => { trainer.miss(); trainerStatus(); };

  $("export-btn").onclick = (e) => { e.stopPropagation(); toggleMenu($("export-menu").hidden); };
  document.addEventListener("click", () => toggleMenu(false));

  $("add-song").onclick = $("empty-pick").onclick = () => $("file-input").click();
  $("file-input").onchange = (e) => { const f = e.target.files[0]; e.target.value = ""; if (f) upload(f); };
  $("song-select").onchange = (e) => openSong(e.target.value).catch(report);
  $("song-title").onclick = async () => {
    if (api.mode !== "server" || !state.song) return;
    const title = prompt(t("song.rename"), state.song.title);
    if (!title || title === state.song.title) return;
    state.song.title = await api.rename(state.song.id, title);
    $("song-title").textContent = state.song.title;
    await refreshSongs(state.song.id);
  };

  const langs = $("lang-select");
  for (const [code, name] of LOCALES) langs.add(new Option(name, code));
  langs.value = locale();
  langs.onchange = async () => { await setLocale(langs.value); relabel(); };

  $("theme-toggle").onclick = () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("stemwise.theme", next);
    timeline.refreshTheme();
  };

  player.addEventListener("position", () => { state.anchor = { sample: player.sample, stamp: performance.now() }; if (!player.playing) tick(); updatePlayIcon(); });
  player.addEventListener("looped", onLooped);

  const veil = $("dropveil");
  let depth = 0;
  window.addEventListener("dragenter", (e) => { if (e.dataTransfer?.types?.includes("Files")) { depth++; veil.hidden = false; } });
  window.addEventListener("dragleave", () => { depth = Math.max(0, depth - 1); if (!depth) veil.hidden = true; });
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => {
    e.preventDefault();
    depth = 0;
    veil.hidden = true;
    const file = e.dataTransfer?.files?.[0];
    if (file) upload(file);
  });

  window.addEventListener("keydown", onKey);
}

function applyPrefs() {
  Object.assign(state, unpackPrefs(memory.prefs(localStorage)));
  $("click-toggle").setAttribute("aria-pressed", String(state.click));
  $("click-volume").value = state.clickGain;
  $("count-in").setAttribute("aria-pressed", String(state.countIn));
  $("flats").checked = state.flats;
}

function relabel() {
  if (state.song) {
    for (const strip of $("strips").children) strip.querySelector(".name").textContent = stemLabel(strip.dataset.stem);
    $("chip-demo").textContent = t("demo.chip");
    renderCredit(state.song);
    updateLoopUi();
    setTrainer(state.trainerOn);
    updatePlayIcon();
    tick();
  }
  refreshSongs(state.song?.id);
}

function onKey(e) {
  if (e.target.closest("input[type=number], select") || e.metaKey || e.ctrlKey || e.altKey || !state.song) return;
  if (document.body.dataset.view !== "studio") return;
  const k = e.key;
  const handled = {
    " ": () => togglePlay().catch(report),
    l: () => $("loop-toggle").click(),
    c: () => $("click-toggle").click(),
    x: () => $("tr-miss").click(),
    Escape: () => $("loop-clear").click(),
    "[": () => setTempo(state.tempo - 5),
    "]": () => setTempo(state.tempo + 5),
    ArrowLeft: () => (e.shiftKey ? resizeLoopBy(-1) : seekRelativeBars(-1)),
    ArrowRight: () => (e.shiftKey ? resizeLoopBy(1) : seekRelativeBars(1)),
    ArrowUp: () => setPitch(state.pitch + 1),
    ArrowDown: () => setPitch(state.pitch - 1),
    Home: () => $("restart").click(),
  }[k];
  if (handled) { e.preventDefault(); handled(); return; }
  if (/^[1-6]$/.test(k)) { e.preventDefault(); toggleSet(state.muted, STEMS[Number(k) - 1]); }
}

async function main() {
  document.documentElement.dataset.theme = localStorage.getItem("stemwise.theme") || "dark";
  await initLocale();
  timeline = new Timeline($("timeline"), {
    onSeek: (time) => player.seek(time),
    onLoop: (start, end) => setLoop({ start, end }),
  });
  timeline.setLabelFn(chordLabel);
  wire();
  applyPrefs();
  requestAnimationFrame(frame);
  await api.detect();
  const songs = await refreshSongs();
  const last = memory.last(localStorage);
  if (api.mode === "demo") $("add-song").hidden = true;
  if (songs.length) {
    const pick = songs.find((s) => s.id === last) || songs.find((s) => s.status === "ready") || songs[0];
    await openSong(pick.id);
  } else {
    show("empty");
  }
}

main().catch((err) => {
  report(err);
  show("empty");
});

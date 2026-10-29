// Chord naming, transposition and fingerings. Pure functions, no DOM.

const SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const ROOT_INDEX = new Map(SHARP.map((n, i) => [n, i]).concat(FLAT.map((n, i) => [n, i])));

/** "F#m7" -> {root: 6, quality: "m7"}. "N" and unknown labels give null. */
export function parseChord(label) {
  const match = /^([A-G][#b]?)(m7|m|7|)$/.exec(label || "");
  if (!match) return null;
  return { root: ROOT_INDEX.get(match[1]), quality: match[2] };
}

export function chordName(chord, flats = false) {
  if (!chord) return "N.C.";
  return (flats ? FLAT : SHARP)[chord.root] + chord.quality;
}

export function transposeLabel(label, semitones, flats = false) {
  const chord = parseChord(label);
  if (!chord) return label === "N" ? "N.C." : label;
  return chordName({ root: (((chord.root + semitones) % 12) + 12) % 12, quality: chord.quality }, flats);
}

/** "E major" shifted by some semitones, for the key chip. */
export function transposeKey(key, semitones, flats = false) {
  const [tonic, ...mode] = key.split(" ");
  return [transposeLabel(tonic, semitones, flats), ...mode].join(" ");
}

const INTERVALS = { "": [0, 4, 7], m: [0, 3, 7], 7: [0, 4, 7, 10], m7: [0, 3, 7, 10] };

/** MIDI notes for a root position voicing starting at octave 3 (C3 = 48). */
export function pianoNotes(chord) {
  if (!chord) return [];
  const base = 48 + chord.root;
  return INTERVALS[chord.quality].map((i) => base + i);
}

// Open shapes, low E string to high e. -1 is muted, 0 is open.
const OPEN = {
  C: [-1, 3, 2, 0, 1, 0], Cm7: [-1, 3, 5, 3, 4, 3], C7: [-1, 3, 2, 3, 1, 0],
  D: [-1, -1, 0, 2, 3, 2], Dm: [-1, -1, 0, 2, 3, 1], D7: [-1, -1, 0, 2, 1, 2], Dm7: [-1, -1, 0, 2, 1, 1],
  E: [0, 2, 2, 1, 0, 0], Em: [0, 2, 2, 0, 0, 0], E7: [0, 2, 0, 1, 0, 0], Em7: [0, 2, 0, 0, 0, 0],
  G: [3, 2, 0, 0, 0, 3], G7: [3, 2, 0, 0, 0, 1],
  A: [-1, 0, 2, 2, 2, 0], Am: [-1, 0, 2, 2, 1, 0], A7: [-1, 0, 2, 0, 2, 0], Am7: [-1, 0, 2, 0, 1, 0],
  B7: [-1, 2, 1, 2, 0, 2],
  F: [1, 3, 3, 2, 1, 1],
};

// Movable barre forms: offsets from the barre fret, rooted on the low E or the A string.
const BARRE = {
  E: { "": [0, 2, 2, 1, 0, 0], m: [0, 2, 2, 0, 0, 0], 7: [0, 2, 0, 1, 0, 0], m7: [0, 2, 0, 0, 0, 0] },
  A: { "": [-1, 0, 2, 2, 2, 0], m: [-1, 0, 2, 2, 1, 0], 7: [-1, 0, 2, 0, 2, 0], m7: [-1, 0, 2, 0, 1, 0] },
};
const OPEN_STRING_PITCH = [4, 9, 2, 7, 11, 4]; // E A D G B E as pitch classes

/** Returns {frets: number[6], base: number} where base is the first fret shown. */
export function guitarShape(chord) {
  if (!chord) return null;
  const name = chordName(chord);
  if (OPEN[name]) return { frets: OPEN[name], base: 1 };
  // Prefer the lowest barre position, E form or A form.
  const eFret = (chord.root - OPEN_STRING_PITCH[0] + 12) % 12;
  const aFret = (chord.root - OPEN_STRING_PITCH[1] + 12) % 12;
  const useA = aFret > 0 && aFret < eFret;
  const fret = useA ? aFret : eFret || 12;
  const form = BARRE[useA ? "A" : "E"][chord.quality];
  const frets = form.map((o) => (o < 0 ? -1 : o + fret));
  return { frets, base: fret, barre: !useA || form[0] >= 0 };
}

// SVG chord diagrams: a guitar fretboard box and a short piano keyboard.
import { guitarShape, pianoNotes } from "./chords.js";

const NS = "http://www.w3.org/2000/svg";

function el(name, attrs = {}, parent) {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  parent?.appendChild(node);
  return node;
}

export function guitarSvg(chord) {
  const svg = el("svg", { viewBox: "0 0 92 112", width: 92, height: 112, role: "img", "aria-label": "guitar chord" });
  const shape = guitarShape(chord);
  if (!shape) return svg;
  const left = 14;
  const gap = 12.4;
  const top = 22;
  const fretH = 16;
  const rows = 5;
  for (let s = 0; s < 6; s++) el("line", { x1: left + s * gap, x2: left + s * gap, y1: top, y2: top + rows * fretH, stroke: "currentColor", "stroke-opacity": 0.55 }, svg);
  for (let f = 0; f <= rows; f++) {
    el("line", { x1: left, x2: left + 5 * gap, y1: top + f * fretH, y2: top + f * fretH, stroke: "currentColor", "stroke-opacity": f === 0 && shape.base === 1 ? 1 : 0.55, "stroke-width": f === 0 && shape.base === 1 ? 3 : 1 }, svg);
  }
  if (shape.base > 1) {
    const label = el("text", { x: left - 12, y: top + fretH * 0.7, "font-size": 11, fill: "currentColor", "font-family": "ui-monospace, monospace", "text-anchor": "middle" }, svg);
    label.textContent = shape.base;
  }
  shape.frets.forEach((fret, s) => {
    const x = left + s * gap;
    if (fret < 0) {
      const t = el("text", { x, y: top - 6, "font-size": 11, "text-anchor": "middle", fill: "currentColor", "fill-opacity": 0.7 }, svg);
      t.textContent = "x";
    } else if (fret === 0) {
      el("circle", { cx: x, cy: top - 9, r: 3.4, fill: "none", stroke: "currentColor", "stroke-opacity": 0.7 }, svg);
    } else {
      const row = shape.base > 1 ? fret - shape.base + 1 : fret;
      el("circle", { cx: x, cy: top + (row - 0.5) * fretH, r: 5.4, fill: "var(--accent)" }, svg);
    }
  });
  return svg;
}

const WHITE = [0, 2, 4, 5, 7, 9, 11];
const BLACK = { 1: 0, 3: 1, 6: 3, 8: 4, 10: 5 };

export function pianoSvg(chord, octaves = 2, startMidi = 48) {
  const keyW = 15;
  const whites = octaves * 7;
  const svg = el("svg", { viewBox: `0 0 ${whites * keyW + 2} 64`, width: whites * keyW + 2, height: 64, role: "img", "aria-label": "piano chord" });
  const lit = new Set(pianoNotes(chord));
  for (let i = 0; i < whites; i++) {
    const midi = startMidi + Math.floor(i / 7) * 12 + WHITE[i % 7];
    el("rect", { x: 1 + i * keyW, y: 1, width: keyW - 1, height: 62, rx: 2, fill: lit.has(midi) ? "var(--accent)" : "#f4efe8", stroke: "#1a1612", "stroke-opacity": 0.6 }, svg);
  }
  for (let o = 0; o < octaves; o++) {
    for (const [semi, whiteBefore] of Object.entries(BLACK)) {
      const midi = startMidi + o * 12 + Number(semi);
      const x = 1 + (o * 7 + whiteBefore) * keyW + keyW * 0.68;
      el("rect", { x, y: 1, width: keyW * 0.62, height: 38, rx: 2, fill: lit.has(midi) ? "var(--accent)" : "#26221e", stroke: "#000", "stroke-opacity": 0.5 }, svg);
    }
  }
  return svg;
}

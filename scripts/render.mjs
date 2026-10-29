// Render stems through the browser engine offline: node scripts/render.mjs OUT.raw TEMPO SEMITONES SECONDS STEM.raw...
// Stems are raw interleaved stereo int16 at 44.1 kHz. Output is raw interleaved stereo float32.
import { readFileSync, writeFileSync } from "node:fs";
import { Engine } from "../web/js/engine.js";

const [out, tempo, semitones, seconds, ...files] = process.argv.slice(2);
const SR = 44100;
const stems = files.map((file) => {
  const pcm = new Int16Array(readFileSync(file).buffer.slice(0));
  const n = pcm.length / 2;
  const l = new Int16Array(n);
  const r = new Int16Array(n);
  for (let i = 0; i < n; i++) { l[i] = pcm[2 * i]; r[i] = pcm[2 * i + 1]; }
  return { l, r };
});
const engine = new Engine(SR);
engine.setStems(stems);
engine.setTempo(Number(tempo));
engine.setPitchSemitones(Number(semitones));
engine.play();
const frames = Math.round(Number(seconds) * SR);
const buf = new Float32Array(frames * 2);
const l = new Float32Array(128);
const r = new Float32Array(128);
for (let i = 0; i < frames; i += 128) {
  engine.process(l, r, 128);
  for (let j = 0; j < 128 && i + j < frames; j++) { buf[2 * (i + j)] = l[j]; buf[2 * (i + j) + 1] = r[j]; }
}
writeFileSync(out, Buffer.from(buf.buffer));

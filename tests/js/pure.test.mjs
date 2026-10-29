import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { parseChord, chordName, transposeLabel, transposeKey, pianoNotes, guitarShape } from "../../web/js/chords.js";
import { Trainer } from "../../web/js/trainer.js";
import { computePeaks, barIndexAt, snapToBars } from "../../web/js/peaks.js";
import { pickLocale, format, LOCALES } from "../../web/js/i18n.js";

test("chords parse and name", () => {
  assert.deepEqual(parseChord("F#m7"), { root: 6, quality: "m7" });
  assert.equal(parseChord("N"), null);
  assert.equal(chordName(parseChord("Bb")), "A#");
  assert.equal(chordName(parseChord("A#"), true), "Bb");
});

test("the key follows the transpose", () => {
  assert.equal(transposeKey("E major", 2), "F# major");
  assert.equal(transposeKey("A minor", -3), "F# minor");
  assert.equal(transposeKey("E major", 2, true), "Gb major");
});

test("transpose wraps and handles no chord", () => {
  assert.equal(transposeLabel("A", 3), "C");
  assert.equal(transposeLabel("C", -1), "B");
  assert.equal(transposeLabel("G7", 5, true), "C7");
  assert.equal(transposeLabel("N", 2), "N.C.");
});

test("piano voicing", () => {
  assert.deepEqual(pianoNotes(parseChord("C")), [48, 52, 55]);
  assert.deepEqual(pianoNotes(parseChord("Am7")), [57, 60, 64, 67]);
});

test("guitar shapes: every sounding string belongs to the chord", () => {
  const open = [4, 9, 2, 7, 11, 4];
  const intervals = { "": [0, 4, 7], m: [0, 3, 7], 7: [0, 4, 7, 10], m7: [0, 3, 7, 10] };
  for (let root = 0; root < 12; root++) {
    for (const quality of ["", "m", "7", "m7"]) {
      const chord = { root, quality };
      const shape = guitarShape(chord);
      assert.equal(shape.frets.length, 6);
      const allowed = intervals[quality].map((i) => (root + i) % 12);
      shape.frets.forEach((fret, s) => {
        if (fret < 0) return;
        const pitch = (open[s] + fret) % 12;
        assert.ok(allowed.includes(pitch), `${chordName(chord)} string ${s} fret ${fret} is ${pitch}`);
      });
      const lowest = shape.frets.findIndex((f) => f >= 0);
      assert.equal((open[lowest] + shape.frets[lowest]) % 12, root, `${chordName(chord)} root in bass`);
    }
  }
});

test("trainer raises tempo after clean loops and resets on a miss", () => {
  const tr = new Trainer({ start: 70, step: 5, goal: 80, loops: 3 });
  assert.equal(tr.tempo, 70);
  assert.equal(tr.loopFinished(), false);
  assert.equal(tr.loopFinished(), false);
  tr.miss();
  assert.equal(tr.loopFinished(), false);
  assert.equal(tr.loopFinished(), false);
  assert.equal(tr.loopFinished(), true);
  assert.equal(tr.tempo, 75);
  for (let i = 0; i < 2; i++) tr.loopFinished();
  assert.equal(tr.loopFinished(), true);
  assert.equal(tr.tempo, 80);
  assert.ok(tr.done);
  for (let i = 0; i < 6; i++) assert.equal(tr.loopFinished(), false);
  assert.equal(tr.tempo, 80);
});

test("trainer clamps nonsense settings", () => {
  const tr = new Trainer({ start: 5, step: 0, goal: 900, loops: "x" });
  assert.equal(tr.start, 25);
  assert.equal(tr.step, 1);
  assert.equal(tr.goal, 150);
  assert.equal(tr.loops, 1);
});

test("peaks keep min and max per bin", () => {
  const l = Int16Array.from([0, 100, -200, 50, 0, 0, 1000, -1000]);
  const p = computePeaks(l, l, 4);
  assert.equal(p.length, 8);
  assert.ok(Math.abs(p[1] - 100 / 32768) < 1e-6);
  assert.ok(Math.abs(p[2] - -200 / 32768) < 1e-6);
  assert.ok(Math.abs(p[7] - 1000 / 32768) < 1e-6);
});

test("bar lookup and snapping", () => {
  const d = [1, 3, 5, 7];
  assert.equal(barIndexAt(d, 0.5), -1);
  assert.equal(barIndexAt(d, 3), 1);
  assert.equal(barIndexAt(d, 6.9), 2);
  assert.deepEqual(snapToBars(d, 9, 3.4, 5.5), [3, 7]);
  assert.deepEqual(snapToBars(d, 9, 5.5, 3.4), [3, 7]);
  assert.deepEqual(snapToBars(d, 9, 7.5, 8.5), [7, 9]);
  assert.deepEqual(snapToBars(d, 9, 0, 0.5), [1, 3]);
});

test("locale negotiation", () => {
  assert.equal(pickLocale(["zh-Hant-TW"]), "zh-TW");
  assert.equal(pickLocale(["zh"]), "zh-CN");
  assert.equal(pickLocale(["pt-PT"]), "pt-BR");
  assert.equal(pickLocale(["fr-CA", "en"]), "fr");
  assert.equal(pickLocale(["sv"]), "en");
  assert.equal(format("Bar {n} of {total}", { n: 2 }), "Bar 2 of {total}");
});

test("every locale has exactly the English keys and placeholders", () => {
  const dir = new URL("../../web/locales/", import.meta.url);
  const en = JSON.parse(readFileSync(new URL("en.json", dir), "utf8"));
  const holders = (s) => (s.match(/\{\w+\}/g) || []).sort().join();
  assert.deepEqual(readdirSync(dir).map((f) => f.replace(".json", "")).sort(), LOCALES.map(([c]) => c).sort());
  for (const [code] of LOCALES) {
    const loc = JSON.parse(readFileSync(new URL(`${code}.json`, dir), "utf8"));
    assert.deepEqual(Object.keys(loc).sort(), Object.keys(en).sort(), code);
    for (const key of Object.keys(en)) {
      assert.equal(holders(loc[key]), holders(en[key]), `${code} ${key}`);
      assert.ok(loc[key].trim().length > 0, `${code} ${key} empty`);
    }
  }
});

test("every key used in code and HTML exists in English", () => {
  const en = JSON.parse(readFileSync(new URL("../../web/locales/en.json", import.meta.url), "utf8"));
  const src = ["index.html", "js/app.js"].map((f) => readFileSync(new URL(`../../web/${f}`, import.meta.url), "utf8")).join("\n");
  const used = new Set();
  for (const m of src.matchAll(/data-i18n(?:-title)?="([\w.]+)"/g)) used.add(m[1]);
  for (const m of src.matchAll(/\bt\("([\w.]+)"/g)) used.add(m[1]);
  for (const m of src.matchAll(/\bt\(`([\w.]+)\$\{/g)) for (const k of Object.keys(en)) if (k.startsWith(m[1])) used.add(k);
  for (const m of src.matchAll(/t\((?:state\.trainerOn|player\.playing|on) \? "([\w.]+)" : "([\w.]+)"/g)) { used.add(m[1]); used.add(m[2]); }
  for (const m of src.matchAll(/t\(`([\w.]+)\.\$\{/g)) void m;
  for (const key of used) assert.ok(key in en, `missing key ${key}`);
});

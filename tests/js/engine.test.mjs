import assert from "node:assert/strict";
import { test } from "node:test";
import { Engine } from "../../web/js/engine.js";

const SR = 44100;

function sine(freq, seconds, amp = 0.5) {
  const n = Math.round(seconds * SR);
  const l = new Float32Array(n);
  for (let i = 0; i < n; i++) l[i] = amp * Math.sin((2 * Math.PI * freq * i) / SR);
  return { l, r: l.slice() };
}

function render(engine, seconds) {
  const n = Math.round(seconds * SR);
  const out = new Float32Array(n);
  const tmp = new Float32Array(128);
  for (let i = 0; i < n; i += 128) {
    engine.process(tmp, new Float32Array(128), 128);
    out.set(tmp.subarray(0, Math.min(128, n - i)), i);
  }
  return out;
}

function frequency(signal, from, to) {
  let crossings = 0;
  for (let i = from + 1; i < to; i++) if (signal[i - 1] < 0 && signal[i] >= 0) crossings++;
  return crossings / ((to - from) / SR);
}

function rms(signal) {
  let sum = 0;
  for (const v of signal) sum += v * v;
  return Math.sqrt(sum / signal.length);
}

function player(seconds = 8, freq = 440) {
  const e = new Engine(SR);
  e.setStems([sine(freq, seconds)]);
  e.play();
  return e;
}

test("tempo 1 passes the signal through at the same pitch", () => {
  const e = player();
  const out = render(e, 3);
  assert.ok(Math.abs(frequency(out, SR, 3 * SR) - 440) < 3);
  assert.ok(Math.abs(e.position / SR - 3) < 0.1);
  assert.ok(rms(out.subarray(SR)) > 0.3);
});

for (const tempo of [0.5, 0.7, 1.5]) {
  test(`tempo ${tempo} changes speed and keeps pitch`, () => {
    const e = player(20);
    e.setTempo(tempo);
    const out = render(e, 4);
    assert.ok(Math.abs(frequency(out, SR, 4 * SR) - 440) < 6, "pitch drifted");
    assert.ok(Math.abs(e.position / SR - 4 * tempo) < 0.15, `position ${e.position / SR}`);
  });
}

for (const semitones of [-5, 2, 7]) {
  test(`pitch ${semitones} semitones keeps speed`, () => {
    const e = player(20);
    e.setPitchSemitones(semitones);
    const out = render(e, 3);
    const want = 440 * Math.pow(2, semitones / 12);
    assert.ok(Math.abs(frequency(out, SR, 3 * SR) - want) < want * 0.015, "wrong pitch");
    assert.ok(Math.abs(e.position / SR - 3) < 0.15, `position ${e.position / SR}`);
  });
}

test("tempo and pitch combine independently", () => {
  const e = player(20);
  e.setTempo(0.7);
  e.setPitchSemitones(3);
  const out = render(e, 4);
  const want = 440 * Math.pow(2, 3 / 12);
  assert.ok(Math.abs(frequency(out, SR, 4 * SR) - want) < want * 0.015);
  assert.ok(Math.abs(e.position / SR - 4 * 0.7) < 0.15);
});

test("muting a stem silences it and the rest keeps playing", () => {
  const e = new Engine(SR);
  e.setStems([sine(220, 6), sine(660, 6)]);
  e.setGains([0, 1]);
  e.play();
  const out = render(e, 2);
  assert.ok(Math.abs(frequency(out, SR / 2, 2 * SR) - 660) < 5);
});

test("a loop wraps and counts passes", () => {
  const e = player(12);
  e.setLoop(1 * SR, 2.5 * SR, true);
  e.seek(1 * SR);
  const out = render(e, 8);
  assert.ok(e.loops >= 4, `loops ${e.loops}`);
  assert.ok(e.position >= 0.9 * SR && e.position <= 2.7 * SR);
  assert.ok(rms(out.subarray(SR)) > 0.3, "loop wrap must not drop out");
  let worst = 0;
  for (let i = SR + 1; i < out.length; i++) worst = Math.max(worst, Math.abs(out[i] - out[i - 1]));
  assert.ok(worst < 0.3, `click at the loop point, step ${worst}`);
});

test("the click follows the beat grid and the tempo", () => {
  for (const [tempo, expected] of [[1, 6], [0.5, 3]]) {
    const e = new Engine(SR);
    e.setStems([sine(100, 20, 0)]);
    e.setClick(true, Array.from({ length: 40 }, (_, i) => (i + 1) * 0.5), [0.5], 1);
    e.setTempo(tempo);
    e.play();
    const out = render(e, 3.2);
    let bursts = 0;
    let quiet = 0;
    for (let i = 0; i < out.length; i++) {
      if (Math.abs(out[i]) > 0.05) { if (quiet > 0.1 * SR || bursts === 0) bursts++; quiet = 0; } else quiet++;
    }
    assert.ok(Math.abs(bursts - expected) <= 1, `tempo ${tempo}: ${bursts} clicks, wanted ${expected}`);
  }
});

test("the engine stops at the end of the song", () => {
  const e = player(1.5);
  render(e, 3);
  assert.equal(e.playing, false);
  assert.ok(e.ended);
});

test("seeking moves the position", () => {
  const e = player(10);
  render(e, 0.5);
  e.seek(6 * SR);
  render(e, 0.5);
  assert.ok(Math.abs(e.position / SR - 6.5) < 0.15, `position ${e.position / SR}`);
});

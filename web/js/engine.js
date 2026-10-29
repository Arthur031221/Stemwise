// Real-time multi-stem player core: a WSOLA time stretcher followed by a resampler.
// Tempo and pitch are independent. Nothing here touches Web Audio globals, so it runs in
// an AudioWorklet and in Node tests alike.

export const FRAME = 2048;
export const HOP = FRAME / 2;
const SEARCH = 512; // WSOLA search radius in samples (about 11 ms at 44.1 kHz)
const RING = 1 << 14;
const MASK = RING - 1;
const CLICK_LEN = 2400;

const WINDOW = new Float32Array(FRAME);
for (let i = 0; i < FRAME; i++) WINDOW[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / FRAME);

export class Engine {
  constructor(sampleRate) {
    this.sampleRate = sampleRate;
    this.stems = [];
    this.gains = new Float32Array(0);
    this.length = 0;
    this.tempo = 1;
    this.pitchRatio = 1;
    this.loop = { on: false, start: 0, end: 0 };
    this.click = { on: false, beats: new Float64Array(0), downbeats: new Set(), gain: 0.5 };
    this.volume = 1;
    this.playing = false;
    this.fade = 0;
    this.loops = 0;
    this.ended = false;

    this.mixL = new Float32Array(FRAME + 2 * SEARCH);
    this.mixR = new Float32Array(FRAME + 2 * SEARCH);
    this.monoRef = new Float32Array(HOP);
    this.monoCand = new Float32Array(HOP + 2 * SEARCH);
    this.refL = new Float32Array(HOP);
    this.refR = new Float32Array(HOP);
    this.olaL = new Float32Array(FRAME);
    this.olaR = new Float32Array(FRAME);
    this.ringL = new Float32Array(RING);
    this.ringR = new Float32Array(RING);
    this.voices = [];
    this.seek(0);
  }

  /** stems: array of {l, r} Int16Array or Float32Array, all the same length. */
  setStems(stems) {
    this.stems = stems;
    this.length = stems.length ? stems[0].l.length : 0;
    this.gains = new Float32Array(stems.length).fill(1);
    this.seek(0);
  }

  setGains(gains) { this.gains = Float32Array.from(gains); }

  setTempo(tempo) { this.tempo = Math.min(2, Math.max(0.25, tempo)); }

  setPitchSemitones(semitones) { this.pitchRatio = Math.pow(2, semitones / 12); }

  setLoop(startSample, endSample, on) {
    this.loop = { on: !!on && endSample - startSample > FRAME, start: startSample, end: endSample };
  }

  setClick(on, beatSeconds, downbeatSeconds, gain = 0.5) {
    const beats = Float64Array.from(beatSeconds, (s) => s * this.sampleRate);
    this.click = {
      on,
      beats,
      downbeats: new Set(downbeatSeconds.map((s) => Math.round(s * this.sampleRate))),
      gain,
    };
    this.lastFired = this._firstBeatAtOrAfter(this.nominal) - 1;
  }

  /** Pressing play after the song ran out starts it again, from the loop start when a loop is on. */
  play() {
    if (this.ended) this.seek(this.loop.on ? this.loop.start : 0);
    this.playing = true;
  }
  pause() { this.playing = false; }

  seek(sample) {
    this.nominal = Math.max(0, Math.min(sample, Math.max(0, this.length - 1)));
    this.hasPrev = false;
    this.prevStart = 0;
    this.ended = false;
    this.sw = this.sw || 0;
    this.rp = this.sw;
    this.blocks = [{ abs: this.sw, nominal: this.nominal }];
    this.olaL.fill(0);
    this.olaR.fill(0);
    this.lastFired = this._firstBeatAtOrAfter(this.nominal) - 1;
  }

  /** Source position, in samples, of the audio being heard right now. */
  get position() {
    let blk = this.blocks[0];
    for (const b of this.blocks) if (b.abs <= this.rp) blk = b;
    return Math.min(this.length, blk.nominal + Math.max(0, this.rp - blk.abs) * this._stretch());
  }

  /** Source samples consumed per stretched sample. */
  _stretch() { return this.tempo / this.pitchRatio; }

  _firstBeatAtOrAfter(sample) {
    const b = this.click ? this.click.beats : [];
    let lo = 0;
    let hi = b.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (b[mid] < sample) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  }

  _mix(start, len, outL, outR) {
    outL.fill(0, 0, len);
    outR.fill(0, 0, len);
    const from = Math.max(0, start);
    const to = Math.min(this.length, start + len);
    if (to <= from) return;
    for (let s = 0; s < this.stems.length; s++) {
      const g = this.gains[s];
      if (g < 1e-4) continue;
      const stem = this.stems[s];
      const scale = stem.l instanceof Int16Array ? g / 32768 : g;
      const l = stem.l;
      const r = stem.r;
      for (let i = from; i < to; i++) {
        outL[i - start] += l[i] * scale;
        outR[i - start] += r[i] * scale;
      }
    }
  }

  /** Choose where in the source the next frame starts. Returns the sample index. */
  _chooseFrame(nominal) {
    const lo = Math.round(nominal) - SEARCH;
    this._mix(lo, FRAME + 2 * SEARCH, this.mixL, this.mixR);
    if (!this.hasPrev) return Math.round(nominal);
    this._mix(this.prevStart + HOP, HOP, this.refL, this.refR);
    const ref = this.monoRef;
    const cand = this.monoCand;
    for (let i = 0; i < HOP; i++) ref[i] = this.refL[i] + this.refR[i];
    for (let i = 0; i < HOP + 2 * SEARCH; i++) cand[i] = this.mixL[i] + this.mixR[i];
    let best = SEARCH;
    let bestScore = -Infinity;
    const score = (lag) => {
      let dot = 0;
      let energy = 1e-9;
      for (let j = 0; j < HOP; j += 2) {
        const c = cand[lag + j];
        dot += ref[j] * c;
        energy += c * c;
      }
      return dot / Math.sqrt(energy);
    };
    for (let lag = 0; lag <= 2 * SEARCH; lag += 2) {
      const sc = score(lag);
      if (sc > bestScore) { bestScore = sc; best = lag; }
    }
    for (const lag of [best - 1, best + 1]) {
      if (lag < 0 || lag > 2 * SEARCH) continue;
      const sc = score(lag);
      if (sc > bestScore) { bestScore = sc; best = lag; }
    }
    return lo + best;
  }

  /** Make one block of HOP stretched samples and append it to the ring. */
  _produce() {
    const hopIn = HOP * this._stretch();
    if (this.loop.on && this.nominal >= this.loop.end) {
      this.nominal = this.loop.start + (this.nominal - this.loop.end);
      this.hasPrev = false;
      this.loops++;
    }
    if (this.nominal >= this.length) {
      this.ended = true;
      this._append(null, 0);
      return;
    }
    const start = this._chooseFrame(this.nominal);
    const offset = start - (Math.round(this.nominal) - SEARCH);
    for (let i = 0; i < FRAME; i++) {
      const w = WINDOW[i];
      this.olaL[i] += this.mixL[offset + i] * w;
      this.olaR[i] += this.mixR[offset + i] * w;
    }
    const srcStart = this.hasPrev ? 0.5 * (this.prevStart + start + HOP) : start;
    this._append(this.olaL, this.olaR, srcStart, this.hasPrev, this.nominal);
    this.olaL.copyWithin(0, HOP);
    this.olaR.copyWithin(0, HOP);
    this.olaL.fill(0, HOP);
    this.olaR.fill(0, HOP);
    this.prevStart = start;
    this.hasPrev = true;
    this.nominal += hopIn;
  }

  _append(l, r, srcStart = 0, continuous = false, nominal = 0) {
    const base = this.sw;
    for (let i = 0; i < HOP; i++) {
      const idx = (base + i) & MASK;
      this.ringL[idx] = l ? l[i] : 0;
      this.ringR[idx] = r ? r[i] : 0;
    }
    if (l && this.click.on) this._addClicks(base, srcStart, continuous);
    this.sw += HOP;
    if (l) {
      this.blocks.push({ abs: base, nominal });
      if (this.blocks.length > 6) this.blocks.shift();
    }
  }

  _addClicks(base, srcStart, continuous) {
    const beats = this.click.beats;
    let i = this.lastFired + 1;
    const limit = srcStart + HOP;
    while (i < beats.length && beats[i] < limit) {
      if (continuous || beats[i] >= srcStart) {
        const offset = Math.min(HOP - 1, Math.max(0, Math.round(beats[i] - srcStart)));
        const strong = this.click.downbeats.has(Math.round(beats[i]));
        this.voices.push({ at: base + offset, age: 0, freq: strong ? 1760 : 1175, strong });
      }
      this.lastFired = i;
      i++;
    }
    const gain = this.click.gain * 0.6;
    const p = this.pitchRatio;
    for (const v of this.voices) {
      for (let abs = Math.max(base, v.at); abs < base + HOP && v.age < CLICK_LEN; abs++, v.age++) {
        const t = v.age / this.sampleRate;
        const env = Math.exp(-v.age / (CLICK_LEN / 6)) * Math.min(1, v.age / 24);
        // the resampler multiplies pitch by p, so the click is generated at freq / p
        const s = Math.sin(2 * Math.PI * (v.freq / p) * t) * env * gain * (v.strong ? 1 : 0.7);
        this.ringL[abs & MASK] += s;
        this.ringR[abs & MASK] += s;
      }
    }
    this.voices = this.voices.filter((v) => v.age < CLICK_LEN);
  }

  /** Render n frames into outL/outR. */
  process(outL, outR, n) {
    const rampStep = 1 / (0.012 * this.sampleRate);
    for (let i = 0; i < n; i++) {
      this.fade += this.playing ? rampStep : -rampStep;
      this.fade = Math.min(1, Math.max(0, this.fade));
      if (this.fade <= 0 && !this.playing) { outL[i] = 0; outR[i] = 0; continue; }
      if (!this.ended) while (this.sw < this.rp + 3) this._produce();
      if (this.ended && this.rp + 3 > this.sw) {
        this.playing = false;
        outL[i] = 0; outR[i] = 0;
        continue;
      }
      const k = Math.floor(this.rp);
      const f = this.rp - k;
      const g = this.fade * this.volume;
      outL[i] = cubic(this.ringL, k, f) * g;
      outR[i] = cubic(this.ringR, k, f) * g;
      this.rp += this.pitchRatio;
    }
  }
}

function cubic(ring, k, f) {
  const a = ring[(k - 1) & MASK];
  const b = ring[k & MASK];
  const c = ring[(k + 1) & MASK];
  const d = ring[(k + 2) & MASK];
  return b + 0.5 * f * (c - a + f * (2 * a - 5 * b + 4 * c - d + f * (3 * (b - c) + d - a)));
}

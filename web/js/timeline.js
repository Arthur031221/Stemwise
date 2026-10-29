// One canvas that draws the ruler, chord lane and one waveform lane per stem.
import { barIndexAt, snapToBars } from "./peaks.js";

export const RULER_H = 28;
export const CHORD_H = 44;
export const HEAD_H = RULER_H + CHORD_H;
export const LANE_H = 64;
export const PEAKS_PER_SECOND = 200;

export class Timeline {
  constructor(canvas, { onSeek, onLoop }) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.onSeek = onSeek;
    this.onLoop = onLoop;
    this.song = null;
    this.stems = [];
    this.muted = new Set();
    this.time = 0;
    this.loop = null;
    this.drag = null;
    this.viewStart = 0;
    this.viewSpan = 1;
    this.follow = true;
    this.label = (l) => l;
    this.dirty = true;
    this.colors = {};
    this.refreshTheme();
    new ResizeObserver(() => this.resize()).observe(canvas.parentElement);
    canvas.addEventListener("pointerdown", (e) => this.down(e));
    canvas.addEventListener("pointermove", (e) => this.move(e));
    canvas.addEventListener("pointerup", (e) => this.up(e));
    canvas.addEventListener("pointercancel", () => { this.drag = null; this.invalidate(); });
    canvas.addEventListener("wheel", (e) => this.wheel(e), { passive: false });
    const tick = () => { if (this.dirty) { this.dirty = false; this.draw(); } requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }

  get height() { return HEAD_H + this.stems.length * LANE_H; }

  setSong(song, stems) {
    this.song = song;
    this.stems = stems; // [{name, peaks}]
    this.viewStart = 0;
    this.viewSpan = song.duration;
    this.loop = null;
    this.time = 0;
    this.resize();
  }

  setMuted(set) { this.muted = set; this.invalidate(); }
  setLabelFn(fn) { this.label = fn; this.invalidate(); }
  setLoop(range) { this.loop = range; this.invalidate(); }

  setTime(t) {
    this.time = t;
    if (this.follow && this.song && this.viewSpan < this.song.duration * 0.98) {
      if (t < this.viewStart || t > this.viewStart + this.viewSpan * 0.9) this.viewStart = this.clampStart(t - this.viewSpan * 0.1);
    }
    this.invalidate();
  }

  refreshTheme() {
    const css = getComputedStyle(document.documentElement);
    const get = (name) => css.getPropertyValue(name).trim();
    this.colors = {
      laneA: get("--lane-a"), laneB: get("--lane-b"), line: get("--line"), text: get("--text"),
      muted: get("--muted"), accent: get("--accent"), panel2: get("--panel2"), accentInk: get("--accent-ink"),
      stem: Object.fromEntries(["vocals", "drums", "bass", "guitar", "piano", "other"].map((n) => [n, get(`--c-${n}`)])),
    };
    this.invalidate();
  }

  invalidate() { this.dirty = true; }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    const width = this.canvas.parentElement.clientWidth;
    const height = this.height;
    this.canvas.width = Math.round(width * dpr);
    this.canvas.height = Math.round(height * dpr);
    this.canvas.style.height = `${height}px`;
    this.width = width;
    this.dpr = dpr;
    this.invalidate();
  }

  clampStart(start) {
    return Math.max(0, Math.min(start, (this.song?.duration ?? 0) - this.viewSpan));
  }

  zoom(factor, anchorTime = this.time) {
    if (!this.song) return;
    const span = Math.max(4, Math.min(this.song.duration, this.viewSpan / factor));
    const ratio = (anchorTime - this.viewStart) / this.viewSpan;
    this.viewSpan = span;
    this.viewStart = this.clampStart(anchorTime - ratio * span);
    this.invalidate();
  }

  wheel(e) {
    if (!this.song) return;
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) {
      this.zoom(e.deltaY < 0 ? 1.2 : 1 / 1.2, this.timeAt(e.offsetX));
    } else {
      const delta = (Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY) / this.width;
      this.viewStart = this.clampStart(this.viewStart + delta * this.viewSpan);
      this.invalidate();
    }
  }

  timeAt(x) { return this.viewStart + (x / this.width) * this.viewSpan; }
  xAt(t) { return ((t - this.viewStart) / this.viewSpan) * this.width; }

  down(e) {
    if (!this.song) return;
    this.canvas.setPointerCapture(e.pointerId);
    const t = this.timeAt(e.offsetX);
    this.drag = { from: t, to: t, ruler: e.offsetY < RULER_H, x0: e.offsetX };
    if (!this.drag.ruler) this.onSeek(t);
  }

  move(e) {
    if (!this.drag) return;
    this.drag.to = this.timeAt(e.offsetX);
    if (this.drag.ruler && Math.abs(e.offsetX - this.drag.x0) > 4) this.invalidate();
    else if (!this.drag.ruler) this.onSeek(Math.max(0, Math.min(this.song.duration, this.drag.to)));
  }

  up(e) {
    const drag = this.drag;
    this.drag = null;
    if (!drag?.ruler) return;
    if (Math.abs(e.offsetX - drag.x0) <= 4) {
      this.onSeek(Math.max(0, drag.from));
    } else {
      const [start, end] = snapToBars(this.song.downbeats, this.song.duration, drag.from, drag.to);
      this.onLoop(start, end);
    }
    this.invalidate();
  }

  draw() {
    const { ctx, width, dpr, song, colors } = this;
    if (!song || !width) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, this.height);
    const t0 = this.viewStart;
    const t1 = this.viewStart + this.viewSpan;

    // lane backgrounds
    ctx.fillStyle = colors.panel2;
    ctx.fillRect(0, 0, width, RULER_H);
    ctx.fillStyle = colors.laneA;
    ctx.fillRect(0, RULER_H, width, CHORD_H);
    this.stems.forEach((_, i) => {
      ctx.fillStyle = i % 2 ? colors.laneB : colors.laneA;
      ctx.fillRect(0, HEAD_H + i * LANE_H, width, LANE_H);
    });

    this.drawLoop(t0, t1);
    this.drawGrid(t0, t1);
    this.drawChords(t0, t1);
    this.stems.forEach((stem, i) => this.drawWave(stem, HEAD_H + i * LANE_H, t0, t1));
    if (this.drag?.ruler && Math.abs(this.drag.to - this.drag.from) > 0.05) this.drawPreview();
    this.drawPlayhead();
  }

  drawLoop(t0, t1) {
    if (!this.loop) return;
    const { ctx, colors } = this;
    const x0 = this.xAt(this.loop.start);
    const x1 = this.xAt(this.loop.end);
    if (x1 < 0 || x0 > this.width) return;
    ctx.fillStyle = colors.accent;
    ctx.globalAlpha = 0.14;
    ctx.fillRect(x0, 0, x1 - x0, this.height);
    ctx.globalAlpha = 0.9;
    ctx.fillRect(x0, RULER_H - 5, x1 - x0, 5);
    ctx.globalAlpha = 1;
  }

  drawPreview() {
    const { ctx, colors } = this;
    const [a, b] = snapToBars(this.song.downbeats, this.song.duration, this.drag.from, this.drag.to);
    ctx.fillStyle = colors.accent;
    ctx.globalAlpha = 0.28;
    ctx.fillRect(this.xAt(a), 0, this.xAt(b) - this.xAt(a), this.height);
    ctx.globalAlpha = 1;
  }

  drawGrid(t0, t1) {
    const { ctx, colors, song } = this;
    ctx.font = "600 11px ui-monospace, Menlo, Consolas, monospace";
    ctx.textBaseline = "middle";
    const perBar = this.width / Math.max(1, this.viewSpan / this.barSeconds());
    const labelEvery = perBar < 26 ? Math.ceil(26 / perBar) : 1;

    ctx.strokeStyle = colors.line;
    ctx.lineWidth = 1;
    if (perBar > 70) {
      ctx.beginPath();
      for (const b of song.beats) {
        if (b < t0 || b > t1) continue;
        const x = Math.round(this.xAt(b)) + 0.5;
        ctx.moveTo(x, RULER_H);
        ctx.lineTo(x, this.height);
      }
      ctx.globalAlpha = 0.35;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    ctx.strokeStyle = colors.muted;
    ctx.fillStyle = colors.muted;
    song.downbeats.forEach((d, i) => {
      if (d < t0 - 1 || d > t1) return;
      const x = Math.round(this.xAt(d)) + 0.5;
      ctx.globalAlpha = 0.4;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.height);
      ctx.stroke();
      ctx.globalAlpha = 1;
      if (i % labelEvery === 0) ctx.fillText(String(i + 1), x + 4, RULER_H / 2);
    });
  }

  barSeconds() {
    const d = this.song.downbeats;
    if (d.length > 1) return (d[d.length - 1] - d[0]) / (d.length - 1);
    return 2;
  }

  drawChords(t0, t1) {
    const { ctx, colors, song } = this;
    ctx.font = "700 15px system-ui, sans-serif";
    ctx.textBaseline = "middle";
    const top = RULER_H + 6;
    const h = CHORD_H - 12;
    for (const c of song.chords) {
      if (c.end < t0 || c.start > t1 || c.label === "N") continue;
      const x = this.xAt(c.start);
      const w = this.xAt(c.end) - x;
      if (w < 3) continue;
      const active = this.time >= c.start && this.time < c.end;
      ctx.fillStyle = active ? colors.accent : colors.panel2;
      ctx.beginPath();
      ctx.roundRect(x + 1, top, w - 2, h, 6);
      ctx.fill();
      if (w > 26) {
        ctx.fillStyle = active ? colors.accentInk : colors.text;
        ctx.save();
        ctx.beginPath();
        ctx.rect(x + 1, top, w - 2, h);
        ctx.clip();
        ctx.fillText(this.label(c.label), x + 7, top + h / 2 + 1);
        ctx.restore();
      }
    }
  }

  drawWave(stem, top, t0, t1) {
    const { ctx, colors, width } = this;
    const mid = top + LANE_H / 2;
    const amp = LANE_H / 2 - 5;
    const dim = this.muted.has(stem.name);
    ctx.fillStyle = colors.stem[stem.name];
    ctx.globalAlpha = dim ? 0.18 : 0.9;
    const peaks = stem.peaks;
    const bins = peaks.length / 2;
    ctx.beginPath();
    for (let x = 0; x < width; x++) {
      const a = Math.max(0, Math.floor((this.timeAt(x)) * PEAKS_PER_SECOND));
      const b = Math.min(bins, Math.max(a + 1, Math.ceil(this.timeAt(x + 1) * PEAKS_PER_SECOND)));
      if (a >= bins) break;
      let lo = 0;
      let hi = 0;
      for (let k = a; k < b; k++) {
        if (peaks[2 * k] < lo) lo = peaks[2 * k];
        if (peaks[2 * k + 1] > hi) hi = peaks[2 * k + 1];
      }
      const y0 = mid - hi * amp;
      const y1 = mid - lo * amp;
      ctx.rect(x, y0, 1, Math.max(1, y1 - y0));
    }
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  drawPlayhead() {
    const { ctx, colors } = this;
    const x = Math.round(this.xAt(this.time)) + 0.5;
    if (x < 0 || x > this.width) return;
    ctx.strokeStyle = colors.accent;
    ctx.fillStyle = colors.accent;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, this.height);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x - 6, 0);
    ctx.lineTo(x + 6, 0);
    ctx.lineTo(x, 8);
    ctx.fill();
  }

  barAt(t) { return barIndexAt(this.song.downbeats, t) + 1; }
}

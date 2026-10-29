// Waveform peak extraction. Works on Int16Array or Float32Array.

/** Returns Float32Array of 2*bins values, [min0, max0, min1, max1, ...], scaled to -1..1. */
export function computePeaks(left, right, bins) {
  const out = new Float32Array(bins * 2);
  const scale = left instanceof Int16Array ? 1 / 32768 : 1;
  const per = left.length / bins;
  for (let b = 0; b < bins; b++) {
    const from = Math.floor(b * per);
    const to = Math.max(from + 1, Math.floor((b + 1) * per));
    let lo = 0;
    let hi = 0;
    for (let i = from; i < to; i++) {
      const v = (left[i] + right[i]) * 0.5;
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
    out[2 * b] = lo * scale;
    out[2 * b + 1] = hi * scale;
  }
  return out;
}

/** Index of the bar a time falls in, given downbeat times. -1 before the first downbeat. */
export function barIndexAt(downbeats, time) {
  let lo = 0;
  let hi = downbeats.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (downbeats[mid] <= time) lo = mid + 1;
    else hi = mid;
  }
  return lo - 1;
}

/** Snap a time range to whole bars. Returns [startSeconds, endSeconds] covering both ends. */
export function snapToBars(downbeats, duration, a, b) {
  const lo = Math.min(a, b);
  const hi = Math.max(a, b);
  const first = Math.max(0, barIndexAt(downbeats, lo));
  const last = Math.max(0, barIndexAt(downbeats, hi));
  const start = downbeats.length ? downbeats[first] : 0;
  const end = last + 1 < downbeats.length ? downbeats[last + 1] : duration;
  return [start, end];
}

/** Grow or shrink a loop by whole bars at its end. A loop never gets shorter than one bar. */
export function resizeLoop(downbeats, duration, loop, delta) {
  if (downbeats.length < 2) return loop;
  const first = Math.max(0, barIndexAt(downbeats, loop.start + 0.01));
  const last = Math.max(first, Math.min(downbeats.length - 1, barIndexAt(downbeats, loop.end - 0.01) + delta));
  const [start, end] = snapToBars(downbeats, duration, downbeats[first], downbeats[last]);
  return { start, end };
}

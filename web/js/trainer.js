// Speed trainer: start slow and raise the tempo after a run of loops without a miss.

export class Trainer {
  constructor({ start = 70, step = 5, goal = 100, loops = 3 } = {}) {
    this.configure({ start, step, goal, loops });
  }

  configure({ start, step, goal, loops }) {
    this.start = clamp(start, 25, 150);
    this.step = clamp(step, 1, 25);
    this.goal = clamp(goal, 25, 150);
    this.loops = clamp(loops, 1, 10);
    this.reset();
  }

  reset() {
    this.tempo = this.start;
    this.clean = 0;
    this.done = this.start >= this.goal;
  }

  /** Call when the loop wraps around. Returns true if the tempo changed. */
  loopFinished() {
    if (this.done) return false;
    this.clean += 1;
    if (this.clean < this.loops) return false;
    this.clean = 0;
    const next = Math.min(this.goal, this.tempo + this.step);
    const changed = next !== this.tempo;
    this.tempo = next;
    this.done = next >= this.goal;
    return changed;
  }

  /** The player slipped, so the current run of clean loops starts over. */
  miss() {
    this.clean = 0;
  }

}

function clamp(value, lo, hi) {
  const n = Number(value);
  return Math.min(hi, Math.max(lo, Number.isFinite(n) ? n : lo));
}

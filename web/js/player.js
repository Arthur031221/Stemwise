// Main-thread wrapper around the AudioWorklet engine.

export class Player extends EventTarget {
  constructor() {
    super();
    this.ctx = null;
    this.node = null;
    this.sampleRate = 44100;
    this.sample = 0;
    this.playing = false;
    this.length = 0;
  }

  async init() {
    if (this.ctx) return;
    this.ctx = new AudioContext({ latencyHint: "interactive", sampleRate: 44100 });
    this.sampleRate = this.ctx.sampleRate;
    await this.ctx.audioWorklet.addModule(new URL("./worklet.js", import.meta.url));
    this.node = new AudioWorkletNode(this.ctx, "stemwise", { numberOfInputs: 0, outputChannelCount: [2] });
    this.node.connect(this.ctx.destination);
    this.node.port.onmessage = ({ data }) => {
      if (data.type === "position") {
        this.sample = data.sample;
        this.playing = data.playing;
        this.dispatchEvent(new CustomEvent("position"));
      } else if (data.type === "looped") {
        this.dispatchEvent(new CustomEvent("looped", { detail: data.count }));
      }
    };
  }

  /** buffers: AudioBuffer[]. Converted to Int16 so the worklet copy stays small. */
  async load(buffers) {
    await this.init();
    const stems = buffers.map((b) => {
      const l = toInt16(b.getChannelData(0));
      const r = toInt16(b.numberOfChannels > 1 ? b.getChannelData(1) : b.getChannelData(0));
      return { l, r };
    });
    this.length = stems[0].l.length;
    this.sample = 0;
    const loaded = new Promise((resolve) => {
      const onMessage = this.node.port.onmessage;
      this.node.port.onmessage = (ev) => {
        if (ev.data.type === "loaded") { this.node.port.onmessage = onMessage; resolve(); } else onMessage(ev);
      };
    });
    this.node.port.postMessage({ type: "stems", stems }, stems.flatMap((s) => [s.l.buffer, s.r.buffer]));
    await loaded;
  }

  get duration() { return this.length / this.sampleRate; }
  get time() { return this.sample / this.sampleRate; }

  send(msg) { this.node?.port.postMessage(msg); }

  async play() {
    await this.ctx.resume();
    this.send({ type: "play" });
    this.playing = true;
  }

  pause() { this.send({ type: "pause" }); this.playing = false; }

  seek(seconds) {
    const sample = Math.max(0, Math.min(this.length - 1, Math.round(seconds * this.sampleRate)));
    this.sample = sample;
    this.send({ type: "seek", sample });
    this.dispatchEvent(new CustomEvent("position"));
  }

  setGains(gains) { this.send({ type: "gains", gains }); }
  setTempo(value) { this.send({ type: "tempo", value }); }
  setPitch(value) { this.send({ type: "pitch", value }); }
  setVolume(value) { this.send({ type: "volume", value }); }

  setLoop(startSeconds, endSeconds, on) {
    this.send({ type: "loop", start: Math.round(startSeconds * this.sampleRate), end: Math.round(endSeconds * this.sampleRate), on });
  }

  setClick(on, beats, downbeats, gain) { this.send({ type: "click", on, beats, downbeats, gain }); }
}

function toInt16(float) {
  const out = new Int16Array(float.length);
  for (let i = 0; i < float.length; i++) {
    const v = float[i] * 32767;
    out[i] = v > 32767 ? 32767 : v < -32768 ? -32768 : v;
  }
  return out;
}

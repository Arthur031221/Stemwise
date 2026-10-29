// AudioWorklet entry point. The Engine does all the work, this only moves messages.
import { Engine } from "./engine.js";

class StemwiseProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.engine = new Engine(sampleRate);
    this.frames = 0;
    this.lastLoops = 0;
    this.port.onmessage = ({ data }) => this.handle(data);
  }

  handle(msg) {
    const e = this.engine;
    switch (msg.type) {
      case "stems": e.setStems(msg.stems); this.port.postMessage({ type: "loaded" }); break;
      case "gains": e.setGains(msg.gains); break;
      case "tempo": e.setTempo(msg.value); break;
      case "pitch": e.setPitchSemitones(msg.value); break;
      case "volume": e.volume = msg.value; break;
      case "loop": e.setLoop(msg.start, msg.end, msg.on); break;
      case "click": e.setClick(msg.on, msg.beats, msg.downbeats, msg.gain); break;
      case "play": e.play(); break;
      case "pause": e.pause(); break;
      case "seek": e.seek(msg.sample); break;
      default: break;
    }
  }

  process(_inputs, outputs) {
    const [left, right] = outputs[0];
    this.engine.process(left, right || left, left.length);
    this.frames += left.length;
    if (this.engine.loops !== this.lastLoops) {
      this.lastLoops = this.engine.loops;
      this.port.postMessage({ type: "looped", count: this.lastLoops });
    }
    if (this.frames >= 2048) {
      this.frames = 0;
      this.port.postMessage({ type: "position", sample: this.engine.position, playing: this.engine.playing });
    }
    return true;
  }
}

registerProcessor("stemwise", StemwiseProcessor);

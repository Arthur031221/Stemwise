# Architecture

Stemwise has two halves that meet at a folder of FLAC files and a JSON document.

```
upload -> server -> JobQueue (one worker) -> pipeline.analyse
                                               |
                     decode (ffmpeg) -> separate (Demucs htdemucs_6s, 6 stems)
                                               |
                                               +-> beats (beat_this: beats, downbeats, BPM)
                                               +-> chords (CQT chroma, templates, Viterbi, key)
                                               |
                              library/songs/<id>/{meta.json, stems/*.flac}
                                               |
browser <- static web/ + /api/* <--------------+
  engine.js (AudioWorklet): WSOLA time stretch, resampler, mixer, loop, click
```

## Python (`src/stemwise`)

| Module | Role |
| --- | --- |
| `audio.py` | decode with ffmpeg to float32 stereo at 44.1 kHz, write FLAC and WAV |
| `separate.py` | wraps Demucs `htdemucs_6s`. fp32 by default, fp16 only on request |
| `beats.py` | beat and downbeat tracking with beat_this, BPM from the median beat interval |
| `chords.py` | chroma from a CQT of the harmonic stems, chord templates (maj, min, 7, min7) with a bass bias, Viterbi smoothing over beats, Krumhansl-Schmuckler key |
| `pipeline.py` | runs the stages in order, reports progress, returns the metadata |
| `library.py` | content addressed storage, atomic `meta.json` writes |
| `jobs.py` | a single worker thread, because the GPU is the bottleneck |
| `export.py` | backing track, stem zip, chord sheet text and HTML, MIDI beat grid |
| `server.py` | Starlette app: the JSON API, streaming upload with a 1 GiB cap, static files, the local-only guard |
| `cli.py` | `serve`, `split`, `bench`, `doctor` |

Chords are decoded on the beat grid. The chord stage mixes the stems that carry harmony (guitar, piano, bass,
other) and ignores drums and vocals.

## Browser (`web`)

Plain ES modules and CSS. There is no bundler and no framework, so the folder is also the GitHub Pages site.

| File | Role |
| --- | --- |
| `js/engine.js`, `js/worklet.js` | the audio engine. The worklet mixes the six stems, applies WSOLA time stretching and a cubic resampler for pitch, handles the loop, and renders the click |
| `js/player.js` | transport state shared by the UI |
| `js/timeline.js`, `js/peaks.js` | canvas waveform timeline with the beat grid and loop handles |
| `js/chords.js`, `js/diagrams.js` | chord lane and SVG guitar and piano shapes |
| `js/trainer.js` | the speed trainer state machine |
| `js/memory.js` | what the studio keeps in `localStorage`: each song's setup, a few preferences and the last song |
| `js/i18n.js`, `locales/*.json` | strings, nine locales |
| `js/api.js` | fetch wrapper. In demo mode it reads `demo/` instead of `/api` |

### Time stretch and pitch

Tempo and pitch are independent. The worklet reads the source at `tempo * 2^(semitones / 12)` with a cubic
resampler, then WSOLA realigns overlapping windows so the output speed returns to `tempo`. The unit tests check
that the source position advances by exactly the expected number of samples and that tempo and pitch combine
independently.

### Demo mode

On `github.io`, or with `?demo`, the app skips the API probe and loads the song listed in `web/demo/index.json`.
The demo stems are AAC in `.m4a`, to keep the repository small. `scripts/build_demo.py` regenerates them from a
source file.

## Tests

| Suite | Command | What it covers |
| --- | --- | --- |
| Python | `pytest -m "not slow and not e2e"` | chords, library, server routes, exports, upload limits, host guard, with a stub separator |
| JavaScript | `node --test tests/js/*.test.mjs` | the engine's stretch, pitch, loop and click maths, chord diagrams, the speed trainer, locale files |
| End to end | `pytest -m e2e` | a real browser against the demo and against the real server |
| Real models | `pytest -m slow` | Demucs and beat_this on a synthetic clip, needs the weights |

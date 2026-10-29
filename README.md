# Stemwise

A local practice studio. It splits a song into six stems, shows the chords and beats, and slows a loop down without changing the pitch.

122.5x realtime stem separation on an RTX 5090. A 2 minute 3 second song takes 1.00 s (`stemwise bench`, fp32, best of 3 after one warm-up run). On a Ryzen 5 7500F with 3 threads the same song takes 45.2 s, which is 2.7x realtime.

[Live demo](https://arthur031221.github.io/Stemwise/) | [Install](docs/install.md) | [Usage](docs/usage.md) | [Config](docs/config.md) | [Architecture](docs/architecture.md) | [Benchmarks](docs/benchmarks.md)

English | [Traditional Chinese](README.zh-TW.md) | [Simplified Chinese](README.zh-CN.md) | [Japanese](README.ja.md) | [Korean](README.ko.md) | [Spanish](README.es.md) | [French](README.fr.md) | [German](README.de.md) | [Portuguese (Brazil)](README.pt-BR.md)

![Stemwise: mute the drums, loop one bar, slow it to 70 percent, add the click, transpose](assets/demo.gif)

Your files never leave your machine, and I'd rather show you where the chord lane is wrong than hide it.

## Before and after

| Practising one hard bar | A normal player | Stemwise |
| --- | --- | --- |
| Slow a loop to 70% | Varispeed drops the pitch by 6.2 semitones | Pitch stays put. A unit test counts the zero crossings of a 440 Hz sine at 50%, 70% and 150% speed |
| Hear only the bass | Not possible from a stereo file | Solo the bass stem, or mute the other five |
| Get a backing track | Look for a karaoke version | Export the mix without the stems you muted, as WAV |
| Find the chords | Rewind and listen | A chord lane on the beat grid. Root accuracy is 0.739 on strummed guitar and 0.265 on solos (see below) |
| Play along to a click | A metronome you set by hand | A click that follows the song's own beat grid, with a count-in |
| Raise the tempo in steps | Nudge the slider and lose count | The speed trainer adds a step after a set number of clean loops (three by default). Press `X` when you slip and the count starts over |

## Install

It's not on PyPI yet, so install from GitHub. You also need Python 3.10 or newer and ffmpeg.

<details>
<summary>Linux (NVIDIA GPU or CPU)</summary>

```sh
sudo apt install ffmpeg libsndfile1
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

On Linux pip pulls the CUDA build of torch, which is a large download. Add `--extra-index-url https://download.pytorch.org/whl/cpu` for a CPU only install.

</details>

<details>
<summary>macOS (Apple Silicon or Intel)</summary>

```sh
brew install ffmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

Apple Silicon uses the MPS device when torch reports it. I haven't measured speed on a Mac.

</details>

<details>
<summary>Windows</summary>

```powershell
winget install Gyan.FFmpeg
pip install git+https://github.com/Arthur031221/Stemwise
stemwise doctor
```

I haven't run Stemwise on Windows. The CI job covers Linux only.

</details>

The first analysis downloads about 55 MB for Demucs and 81 MB for beat_this. After that nothing needs the network.

## Use it

```sh
stemwise                      # open the studio in your browser
stemwise split song.mp3       # stems, chords.txt and beats.mid in a "song stems" folder
```

Real output from `stemwise split` on a 2 minute song:

```
surf.mp3: 123s, 166.7 BPM, B major, 105 chords, on cuda
```

Drop a file on the page and wait for the progress bar. Click and drag on the ruler to pick a loop, press `L` to loop the bar the playhead is in, and use the keys below. The full list is in [docs/usage.md](docs/usage.md).

| Key | Action | Key | Action |
| --- | --- | --- | --- |
| Space | play and pause | `[` `]` | tempo down and up 5% |
| L | loop this bar, or toggle the loop | Up, Down | transpose a semitone |
| C | click on and off | Left, Right | seek a bar |
| X | miss, for the trainer | 1 to 6 | mute a stem |

## What is in the box

| Part | What it is |
| --- | --- |
| Separation | Demucs v4 `htdemucs_6s`: vocals, drums, bass, guitar, piano, other |
| Beats | beat_this for beats, downbeats and BPM |
| Chords | CQT chroma, major, minor, 7 and min7 templates, Viterbi smoothing and a key estimate. No neural chord model |
| Player | An AudioWorklet engine with WSOLA time stretching, a cubic resampler, loops, a click and a count-in |
| Studio | Plain ES modules and CSS with no build step, nine UI languages, dark and light themes |
| Exports | Backing track, stems zip, chord sheet as text or printable HTML, beat grid as MIDI |
| API | A small local JSON API, documented in [docs/usage.md](docs/usage.md) |

The browser app lives in `web/`, the same folder GitHub Pages serves as the live demo. The demo plays a pre-separated song and can't split your own files.

## How well does it work

I ran `bench/chords_guitarset.py` on [GuitarSet](https://guitarset.weebly.com/) (360 clips of solo guitar). I tuned the chord constants on every fifth clip and scored the other 288.

| Clips | Root | Major and minor | Beat F | Downbeat F |
| --- | --- | --- | --- | --- |
| Accompaniment, 144 | 0.739 | 0.671 | 0.971 | 0.944 |
| Solos, 144 | 0.265 | 0.201 | 0.605 | 0.403 |

Beats on strummed parts are reliable. Chords are a starting point for learning a song, so check them by ear. A single note solo holds almost no chord information, so the lane is mostly wrong there. These clips are solo guitar, so I can't tell you how a full band mix scores. The full table and method are in [docs/benchmarks.md](docs/benchmarks.md).

## Limits

- The chord lane knows four chord types. Slash chords, suspended chords and extensions show up as the nearest of the four.
- The key is one guess for the whole song. In the output above it says B major while the chords are mostly Em, D and Bm, so treat it as a hint.
- The tempo shown is the beat tracker's median, so it can differ from a published tempo. The demo song is listed at 170 BPM and the tracker reports 166.7.
- A song with an instrumental arrangement leaves the vocals and piano stems close to empty. That's the separation working correctly.
- On a CPU a four minute song takes about 90 seconds at the 2.7x I measured, and longer on slower chips.
- Time stretching is WSOLA, which can smear sustained notes at the slowest settings.
- Only one song is processed at a time.

## Development

```sh
pip install -e ".[dev]"
ruff check . && pytest -m "not slow and not e2e"
node --test tests/js/*.test.mjs
STEMWISE_BROWSER_CHANNEL=chrome pytest -m e2e
```

See [CONTRIBUTING.md](CONTRIBUTING.md). A tag that starts with `v` triggers the release workflow, which builds the wheel and sdist and attaches them to a GitHub release.

## Credits and licenses

Stemwise is MIT licensed. It builds on [Demucs](https://github.com/facebookresearch/demucs) (MIT), [beat_this](https://github.com/CPJKU/beat_this) (MIT code and weights), librosa and Starlette. The live demo plays "Surf Shimmy" by Kevin MacLeod ([incompetech.com](https://incompetech.com)), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), cut to a 36 second excerpt and separated with Stemwise. GuitarSet is by Xi et al. (2018), CC BY 4.0.

Assisted by Claude/Codex.

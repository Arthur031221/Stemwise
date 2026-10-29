# Benchmarks

Numbers on this page come from the commands shown. Nothing here is a vendor figure.

## Separation speed

`stemwise bench song.mp3` on a 122.9 second song (a 36 second excerpt of which is the live demo's track).
The first run is a warm-up and is discarded. fp32.

| Device | Separation time | Speed |
| --- | --- | --- |
| NVIDIA RTX 5090 | 1.00 s (best of 3) | 122.5x realtime |
| AMD Ryzen 5 7500F, 3 threads | 45.21 s (1 run) | 2.7x realtime |

The full analysis (decode, separation, beats, chords, FLAC writing) takes longer than the separation alone. On the
same GPU, `stemwise split` reports separation as 2.07 s on a cold start, because the first call pays for CUDA
initialisation.

## Chord and beat accuracy

`python bench/chords_guitarset.py DIR` on [GuitarSet](https://guitarset.weebly.com/) (Xi et al., 2018, CC BY 4.0),
360 clips, scored with `mir_eval`. Every clip goes through the same path the app uses: separate, track beats,
detect chords. The reference is the "instructed" chord annotation.

The chord constants (template set, bass bias, smoothing) were tuned on every fifth clip. The table reports the
other four fifths, 288 clips, duration weighted for chords.

| Subset | Clips | Root | Major/minor | Triads | Sevenths | Beat F | Downbeat F |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Accompaniment (`comp`) | 144 | 0.739 | 0.671 | 0.641 | 0.598 | 0.971 | 0.944 |
| Solo (`solo`) | 144 | 0.265 | 0.201 | 0.192 | 0.186 | 0.605 | 0.403 |
| All | 288 | 0.504 | 0.438 | 0.418 | 0.394 | 0.788 | 0.673 |

How to read this:

- Strummed accompaniment is the use case. Beats and downbeats are tracked well there.
- Single note solos have almost no chord information in the audio, and the annotation is the chord of the
  underlying progression. Do not expect the chord lane to be right on a solo.
- GuitarSet is solo guitar. Full band mixes are harder in some ways and easier in others, so treat these as a
  floor for guitar-led material and not as a promise for every genre.
- Chord names are a starting point for learning a song. Check them by ear.

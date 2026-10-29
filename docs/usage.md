# Usage

## The studio

```sh
stemwise            # same as: stemwise serve
stemwise --port 9000  # flags go to serve as well
```

This starts a server on `127.0.0.1:8765`, opens a browser tab and keeps your songs in a local library. Drop an
audio file on the page. Stemwise separates it into six stems (vocals, drums, bass, guitar, piano, other), tracks
the beats and downbeats, detects the key and the chords, and then opens the player.

In the player:

- Click a stem name to mute it, use the solo button to hear one, and drag the slider to change its level.
- Drag across the timeline to set a loop, or press `L` to loop the bar the playhead is in.
- Change the tempo from 25% to 200% without changing pitch. Transpose by semitones independently.
- Turn on the click and the count-in to practise against a metronome that follows the song's own beat grid.
- The speed trainer starts a loop slow and raises the tempo by a step after a set number of clean passes (three by default). Press `X` to
  mark a miss and the count of clean passes starts over.
- Click a chord to see the guitar and piano shapes for it.

### Keyboard shortcuts

| Key | Action |
| --- | --- |
| Space | play and pause |
| L | loop the current bar, or switch an existing loop on and off |
| C | click track on and off |
| X | mark a miss in the speed trainer |
| Esc | clear the loop |
| [ and ] | tempo down and up by 5 percent |
| Left, Right | next bar, or back to the start of this bar and then the previous one |
| Up, Down | transpose by one semitone |
| Home | restart |
| 1 to 6 | mute or unmute a stem |

### Exports

Each song has an export menu:

- the backing track, which is the mix of every stem you have not muted (WAV, or FLAC with `?format=flac`)
- all stems in one zip
- a chord sheet as plain text or a printable HTML page
- the beat grid as a MIDI file

## From the command line

```sh
stemwise split song.mp3                  # writes "song stems/" next to the file
stemwise split song.mp3 -o out --format wav
stemwise bench song.mp3 --runs 3         # time the separation
stemwise doctor
```

`split` writes one file per stem, `chords.txt` and `beats.mid`. It prints a one line summary:

```
surf.mp3: 123s, 166.7 BPM, B major, 105 chords, on cuda
```

## HTTP API

The studio is a thin client over a small JSON API, so you can script it. It only answers requests whose Host and
Origin are local.

| Route | Purpose |
| --- | --- |
| `GET /api/health` | version and device |
| `GET /api/songs` | list songs |
| `POST /api/songs` | upload a file as the raw request body, with `?name=<file name>` (1 GiB limit) |
| `GET /api/songs/{id}` | metadata, status, stage and progress |
| `PATCH /api/songs/{id}` | rename |
| `DELETE /api/songs/{id}` | remove the song and its stems |
| `GET /api/songs/{id}/stems/{stem}.flac` | one stem |
| `GET /api/songs/{id}/export/{kind}` | `backing`, `stems`, `chords.txt`, `chords.html`, `beats.mid` |

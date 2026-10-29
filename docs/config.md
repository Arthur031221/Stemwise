# Configuration

Stemwise has no config file. Everything is a flag or an environment variable.

## `stemwise serve`

| Flag | Default | Meaning |
| --- | --- | --- |
| `--host` | `127.0.0.1` | bind address |
| `--port` | `8765` | port |
| `--library` | user data folder | where songs are stored |
| `--no-open` | off | do not open a browser tab |

By default the server only answers requests whose Host and Origin headers are local, which blocks DNS rebinding
and cross site uploads. If you pass another `--host`, that address is accepted as a Host too. There is no login,
so only do that on a network you trust, or reach the server through an SSH tunnel instead.
`--host 0.0.0.0` is refused. Give the one address you want, for example `--host 192.168.1.20`.

## `stemwise split` and `stemwise bench`

| Flag | Meaning |
| --- | --- |
| `-o`, `--output` | output folder |
| `--format flac\|wav` | stem file format (split) |
| `--device` | `cuda`, `mps` or `cpu` |
| `--runs` | timed runs (bench) |
| `--fp16` | mixed precision (bench). Faster, but the output is not identical to fp32 |

## Environment

| Variable | Meaning |
| --- | --- |
| `STEMWISE_HOME` | library folder. Wins over everything below |
| `XDG_DATA_HOME` | Linux: library is `$XDG_DATA_HOME/stemwise` |
| `LOCALAPPDATA` | Windows: library is `%LOCALAPPDATA%\stemwise` |
| `STEMWISE_BROWSER_CHANNEL` | tests only: browser channel for Playwright, for example `chrome` |

Without any of these the library is `~/.local/share/stemwise` (Linux, macOS).

## Library layout

```
<library>/songs/<id>/
  meta.json      status, stage, progress, bpm, key, beats, chords, timings
  source.<ext>   the file you uploaded
  stems/*.flac   six stems
```

The id is the first 12 hex characters of the SHA-256 of the file, so uploading the same file twice reuses the
existing song.

## Language

The UI language follows the browser and can be changed from the switcher in the header. The choice is saved in
local storage. Locale files live in `web/locales/` and are plain JSON.

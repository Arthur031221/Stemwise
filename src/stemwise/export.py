"""Exports: backing tracks, stem archives, chord sheets and a MIDI beat map."""

from __future__ import annotations

import html
import io
import struct
import zipfile
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio import SAMPLE_RATE
from .library import Library

PPQ = 480
CLAP_NOTE, CLAVES_NOTE = 39, 75  # General MIDI percussion: hand clap marks the downbeat


def read_stem(path: Path) -> np.ndarray:
    data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    if rate != SAMPLE_RATE:
        raise ValueError(f"unexpected sample rate {rate}")
    return data.T


def encode(audio: np.ndarray, fmt: str) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.clip(audio.T, -1, 1), SAMPLE_RATE, format=fmt.upper(), subtype="PCM_16")
    return buf.getvalue()


def backing_track(library: Library, song_id: str, leave_out: list[str], fmt: str = "wav") -> bytes:
    """Mix every stem except `leave_out`."""
    meta = library.read(song_id)
    names = [s for s in meta["stems"] if s not in leave_out]
    if not names:
        raise ValueError("nothing left to mix")
    mix = sum(read_stem(library.stem_path(song_id, n)) for n in names)
    peak = float(np.abs(mix).max())
    if peak > 1.0:
        mix = mix / peak
    return encode(mix, fmt)


def stems_zip(library: Library, song_id: str) -> bytes:
    meta = library.read(song_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:  # flac is already compressed
        for name in meta["stems"]:
            zf.write(library.stem_path(song_id, name), f"{meta['title']} - {name}.flac")
    return buf.getvalue()


def _bars(meta: dict) -> list[tuple[int, float, list[str]]]:
    """Group the chord changes into bars: (bar number, start time, chord labels in the bar)."""
    starts = list(meta.get("downbeats") or [])
    if not starts:
        return []
    ends = starts[1:] + [meta["duration"]]
    out = []
    for i, (lo, hi) in enumerate(zip(starts, ends, strict=True)):
        labels: list[str] = []
        for ch in meta["chords"]:
            if ch["end"] > lo + 0.05 and ch["start"] < hi - 0.05 and (not labels or labels[-1] != ch["label"]):
                labels.append(ch["label"])
        out.append((i + 1, lo, labels or ["N"]))
    return out


def chord_sheet_text(meta: dict) -> str:
    lines = [meta["title"], f"Key: {meta.get('key', '?')}   Tempo: {meta.get('bpm', '?')} BPM", ""]
    bars = _bars(meta)
    for i in range(0, len(bars), 4):
        row = bars[i : i + 4]
        cells = " | ".join(" ".join(labels).ljust(10) for _, _, labels in row)
        lines.append(f"{row[0][0]:>3}  | {cells} |")
    return "\n".join(lines) + "\n"


def chord_sheet_html(meta: dict) -> str:
    bars = _bars(meta)
    rows = []
    for i in range(0, len(bars), 4):
        cells = "".join(
            f"<td><small>{n}</small>{html.escape(' '.join(labels))}</td>" for n, _, labels in bars[i : i + 4]
        )
        rows.append(f"<tr>{cells}</tr>")
    return (
        "<!doctype html><meta charset=utf-8>"
        f"<title>{html.escape(meta['title'])}</title>"
        "<style>body{font:16px/1.4 system-ui;margin:2rem auto;max-width:46rem;padding:0 1rem}"
        "table{border-collapse:collapse;width:100%}td{border:1px solid #888;padding:.7rem;"
        "font:600 1.1rem ui-monospace,monospace;width:25%}small{display:block;font:11px system-ui;color:#666}"
        "@media print{body{margin:0}}</style>"
        f"<h1>{html.escape(meta['title'])}</h1>"
        f"<p>Key {html.escape(str(meta.get('key', '?')))}, {meta.get('bpm', '?')} BPM</p>"
        f"<table>{''.join(rows)}</table>"
    )


def _varlen(value: int) -> bytes:
    out = [value & 0x7F]
    while value >> 7:
        value >>= 7
        out.append((value & 0x7F) | 0x80)
    return bytes(reversed(out))


def beats_midi(meta: dict) -> bytes:
    """A format 0 MIDI file whose tempo map follows the tracked beats, with a click on every beat."""
    beats = meta.get("beats") or []
    if len(beats) < 2:
        raise ValueError("no beats were tracked for this song")
    downbeats = {round(d, 3) for d in meta.get("downbeats", [])}
    events: list[tuple[int, int, bytes]] = []  # (tick, order, bytes); tempo sorts before notes
    for i, beat in enumerate(beats):
        gap = (beats[i + 1] - beat) if i + 1 < len(beats) else (beat - beats[i - 1])
        micros = max(1, round(gap * 1_000_000))
        note = CLAP_NOTE if round(beat, 3) in downbeats else CLAVES_NOTE
        events.append((i * PPQ, 0, b"\xff\x51\x03" + micros.to_bytes(3, "big")))
        events.append((i * PPQ, 1, bytes([0x99, note, 110])))
        events.append((i * PPQ + PPQ // 2, 2, bytes([0x89, note, 0])))
    events.sort(key=lambda e: (e[0], e[1]))
    track, last = bytearray(), 0
    for tick, _, data in events:
        track += _varlen(tick - last) + data
        last = tick
    track += _varlen(0) + b"\xff\x2f\x00"
    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, PPQ)
    return header + b"MTrk" + struct.pack(">I", len(track)) + bytes(track)

"""The analysis pipeline: decode, separate, write stems, track beats, estimate chords and key."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from . import audio, beats, chords
from .library import Library
from .separate import STEMS, Separator

Report = Callable[[str, float], None]


def analyse(source: Path, stems_dir: Path, separator: Separator, report: Report | None = None) -> dict:
    """Run the whole pipeline on one file and return the analysis (no title or id)."""
    report = report or (lambda stage, fraction: None)
    timings: dict[str, float] = {}

    def timed(name: str, fn):
        start = time.perf_counter()
        result = fn()
        timings[name] = round(time.perf_counter() - start, 2)
        return result

    report("decoding", 0.0)
    mix = timed("decode", lambda: audio.decode(source))
    if mix.shape[-1] < audio.SAMPLE_RATE:
        raise audio.AudioError("this file is shorter than one second")
    duration = audio.duration(mix)

    report("separating", 0.02)
    stems = timed("separate", lambda: separator.split(mix, progress=lambda f: report("separating", 0.02 + 0.78 * f)))

    report("writing", 0.82)
    stems_dir.mkdir(parents=True, exist_ok=True)
    for name, data in stems.items():
        audio.write(stems_dir / f"{name}.flac", data)

    report("beats", 0.88)
    mono = mix.mean(axis=0).astype(np.float32)
    beat_map = timed("beats", lambda: beats.track(mono, separator.device))

    report("chords", 0.94)
    sequence = timed("chords", lambda: chords.detect(stems, beat_map.beats or None))
    key = chords.estimate_key(stems)

    return {
        "duration": round(duration, 2),
        "stems": list(STEMS),
        "bpm": round(beat_map.bpm, 1),
        "key": key,
        "beats": beat_map.beats,
        "downbeats": beat_map.downbeats,
        "chords": [c.to_dict() for c in sequence],
        "device": separator.device,
        "timings": timings,
    }


class SongRemoved(Exception):
    """The song was deleted while its job was running."""


def run_job(library: Library, song_id: str, source: Path, separator: Separator) -> None:
    """Process an uploaded song and keep its meta.json up to date."""

    def update(**fields) -> None:
        """Merge into the current meta.json, so a rename made mid-job survives. A deleted song stays deleted."""
        if not library.exists(song_id):
            raise SongRemoved(song_id)
        meta = library.read(song_id)
        meta.update(fields)
        if fields.get("status") != "error":
            meta.pop("error", None)
        library.write(song_id, meta)

    def report(stage: str, fraction: float) -> None:
        update(status="processing", stage=stage, progress=round(fraction, 3))

    try:
        result = analyse(source, library.folder(song_id) / "stems", separator, report)
        update(**result, status="ready", stage="ready", progress=1.0)
    except SongRemoved:
        library.delete(song_id)  # the analysis may have recreated the folder, make sure nothing is left
    except Exception as exc:  # surfaced to the UI, the job queue must keep running
        try:
            update(status="error", stage="error", error=str(exc) or exc.__class__.__name__)
        except SongRemoved:
            pass

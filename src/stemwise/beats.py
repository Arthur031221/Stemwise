"""Beat and downbeat tracking with beat_this (CPJKU, MIT)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .audio import SAMPLE_RATE


@dataclass
class BeatMap:
    beats: list[float]
    downbeats: list[float]

    @property
    def bpm(self) -> float:
        if len(self.beats) < 2:
            return 0.0
        return float(60.0 / np.median(np.diff(self.beats)))

    def bar_starts(self, duration: float) -> list[float]:
        """Downbeat times, with a leading bar when the song starts before the first downbeat."""
        bars = list(self.downbeats)
        if bars and len(self.beats) > 1 and bars[0] - self.beats[0] > 1e-3:
            bars.insert(0, self.beats[0])
        return [b for b in bars if b < duration]

    def to_dict(self) -> dict:
        return {"beats": self.beats, "downbeats": self.downbeats, "bpm": round(self.bpm, 1)}


_tracker = {}


def _get_tracker(device: str):
    if device not in _tracker:
        from beat_this.inference import Audio2Beats

        _tracker[device] = Audio2Beats(checkpoint_path="final0", device=device, dbn=False)
    return _tracker[device]


def track(mono: np.ndarray, device: str = "cpu") -> BeatMap:
    """Track beats in a mono float32 signal at 44.1 kHz."""
    beats, downbeats = _get_tracker(device)(mono, SAMPLE_RATE)
    return BeatMap([round(float(b), 3) for b in beats], [round(float(d), 3) for d in downbeats])

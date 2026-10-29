"""Chord and key estimation from the harmonic stems.

The detector is deliberately classical: constant-Q chroma, chord templates, and a Viterbi
pass that charges a fixed price for every chord change. It reads the guitar, piano, bass and
other stems, so drums and vocals do not smear the chroma.
"""

from __future__ import annotations

from dataclasses import dataclass

import librosa
import numpy as np
from scipy.signal import resample_poly

from .audio import SAMPLE_RATE

NOTES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
HARMONIC_STEMS = ("guitar", "piano", "other", "bass")
ANALYSIS_RATE = 22050
HOP = 2048

# quality name -> (semitone offsets, weight of each tone, score penalty).
# Constants below were tuned on every fifth GuitarSet clip, see bench/chords_guitarset.py.
QUALITIES: dict[str, tuple[tuple[int, ...], tuple[float, ...], float]] = {
    "maj": ((0, 4, 7), (1.0, 0.9, 0.9), 0.0),
    "min": ((0, 3, 7), (1.0, 0.9, 0.9), 0.0),
    "7": ((0, 4, 7, 10), (1.0, 0.9, 0.9, 0.7), 0.12),
    "min7": ((0, 3, 7, 10), (1.0, 0.9, 0.9, 0.7), 0.12),
}

_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


@dataclass
class Chord:
    start: float
    end: float
    label: str  # "N" for no chord, otherwise "C", "Am", "G7", "Dm7"

    def to_dict(self) -> dict:
        return {"start": round(self.start, 3), "end": round(self.end, 3), "label": self.label}


def label_of(root: int, quality: str) -> str:
    suffix = {"maj": "", "min": "m", "7": "7", "min7": "m7"}[quality]
    return NOTES[root] + suffix


def _templates() -> tuple[np.ndarray, list[tuple[int, str]], np.ndarray]:
    rows, names, penalties = [], [], []
    for quality, (offsets, weights, penalty) in QUALITIES.items():
        for root in range(12):
            vec = np.zeros(12)
            for off, w in zip(offsets, weights, strict=True):
                vec[(root + off) % 12] = w
            rows.append(vec / np.linalg.norm(vec))
            names.append((root, quality))
            penalties.append(penalty)
    return np.array(rows), names, np.array(penalties)


def mixdown(stems: dict[str, np.ndarray], names: tuple[str, ...] = HARMONIC_STEMS) -> np.ndarray:
    """Sum the named stems to mono at the analysis rate."""
    picked = [stems[n] for n in names if n in stems]
    if not picked:
        raise ValueError("no harmonic stems to analyse")
    mono = np.sum(picked, axis=0).mean(axis=0)
    return resample_poly(mono, ANALYSIS_RATE, SAMPLE_RATE).astype(np.float32)


def chroma(signal: np.ndarray) -> np.ndarray:
    """Return a (12, frames) chroma matrix."""
    tuning = librosa.estimate_tuning(y=signal, sr=ANALYSIS_RATE)
    c = librosa.feature.chroma_cqt(
        y=signal,
        sr=ANALYSIS_RATE,
        hop_length=HOP,
        tuning=tuning,
        n_octaves=6,
        fmin=librosa.note_to_hz("C2"),
    )
    return c


def _viterbi(emission: np.ndarray, switch_cost: float) -> np.ndarray:
    """Best state path when every change of state costs `switch_cost` (emission is frames x states)."""
    frames, states = emission.shape
    score = emission[0].copy()
    came_from = np.zeros((frames, states), dtype=np.int32)
    for t in range(1, frames):
        best = int(np.argmax(score))
        stay = score
        jump = score[best] - switch_cost
        use_jump = jump > stay
        came_from[t] = np.where(use_jump, best, np.arange(states))
        score = np.where(use_jump, jump, stay) + emission[t]
    path = np.zeros(frames, dtype=np.int32)
    path[-1] = int(np.argmax(score))
    for t in range(frames - 1, 0, -1):
        path[t - 1] = came_from[t, path[t]]
    return path


def _beat_average(c: np.ndarray, frame_times: np.ndarray, edges: np.ndarray) -> np.ndarray:
    cols = []
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        sel = (frame_times >= lo) & (frame_times < hi)
        cols.append(c[:, sel].mean(axis=1) if sel.any() else np.zeros(c.shape[0]))
    return np.array(cols).T


@dataclass
class Features:
    chroma: np.ndarray  # (12, frames)
    bass: np.ndarray | None  # (12, frames), same frames as `chroma`
    frame_times: np.ndarray
    duration: float


def extract(stems: dict[str, np.ndarray]) -> Features:
    signal = mixdown(stems)
    c = chroma(signal)
    bass = chroma(mixdown(stems, ("bass",))) if "bass" in stems else None
    times = librosa.frames_to_time(np.arange(c.shape[1]), sr=ANALYSIS_RATE, hop_length=HOP)
    return Features(c, bass, times, len(signal) / ANALYSIS_RATE)


def decode(
    feat: Features,
    beats: list[float] | None = None,
    switch_cost: float = 0.15,
    bass_weight: float = 0.6,
    quiet_ratio: float = 0.25,
) -> list[Chord]:
    """Pick the best chord path. With `beats`, chords change only on a beat."""
    c, bass = feat.chroma, feat.bass
    if beats is not None and len(beats) >= 2:
        edges = np.unique(np.concatenate([[0.0], np.asarray(beats), [feat.duration]]))
        c = _beat_average(c, feat.frame_times, edges)
        if bass is not None:
            bass = _beat_average(bass, feat.frame_times, edges)
    else:
        edges = np.append(feat.frame_times, feat.duration)

    templates, names, penalties = _templates()
    unit = c / (np.linalg.norm(c, axis=0, keepdims=True) + 1e-9)
    emission = unit.T @ templates.T - penalties
    if bass is not None:
        bass_unit = bass / (bass.sum(axis=0, keepdims=True) + 1e-9)
        roots = np.array([r for r, _ in names])
        emission = emission + bass_weight * bass_unit.T[:, roots]
    energy = c.sum(axis=0)
    loud = energy[energy > 0]
    quiet = energy < quiet_ratio * np.median(loud) if loud.size else np.ones_like(energy, bool)
    emission = np.hstack([emission, np.where(quiet, 10.0, -10.0)[:, None]])

    path = _viterbi(emission, switch_cost)
    chords: list[Chord] = []
    for i, state in enumerate(path):
        label = "N" if state == len(names) else label_of(*names[state])
        start, end = float(edges[i]), float(edges[i + 1])
        if chords and chords[-1].label == label:
            chords[-1].end = end
        else:
            chords.append(Chord(start, end, label))
    return chords


def detect(stems: dict[str, np.ndarray], beats: list[float] | None = None, **params) -> list[Chord]:
    return decode(extract(stems), beats, **params)


def estimate_key(stems: dict[str, np.ndarray]) -> str:
    """Return a key such as 'A minor', using the Krumhansl-Schmuckler profiles."""
    profile = chroma(mixdown(stems)).mean(axis=1)
    best, best_score = ("C", "major"), -2.0
    for root in range(12):
        for mode, ref in (("major", _MAJOR_PROFILE), ("minor", _MINOR_PROFILE)):
            score = np.corrcoef(profile, np.roll(ref, root))[0, 1]
            if score > best_score:
                best, best_score = (NOTES[root], mode), score
    return f"{best[0]} {best[1]}"

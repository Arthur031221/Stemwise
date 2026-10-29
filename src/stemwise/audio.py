"""Audio decoding and writing. ffmpeg decodes, soundfile writes."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 44100


class AudioError(Exception):
    pass


def decode(path: str | Path, sample_rate: int = SAMPLE_RATE, mono: bool = False) -> np.ndarray:
    """Decode any file ffmpeg understands to float32 with shape (channels, samples)."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise AudioError("ffmpeg was not found on PATH. Install it from https://ffmpeg.org/download.html")
    channels = 1 if mono else 2
    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-nostdin",
        "-i",
        str(path),
        "-vn",
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-ac",
        str(channels),
        "-ar",
        str(sample_rate),
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        detail = proc.stderr.decode(errors="replace").strip().splitlines()
        raise AudioError(detail[-1] if detail else "ffmpeg could not read this file")
    data = np.frombuffer(proc.stdout, dtype=np.float32)
    return np.ascontiguousarray(data.reshape(-1, channels).T)


def write(path: str | Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Write (channels, samples) audio. The format follows the file extension (wav or flac)."""
    suffix = Path(path).suffix.lower()
    if suffix not in (".wav", ".flac"):
        raise AudioError(f"cannot write {suffix or 'this'} files, use .wav or .flac")
    clipped = np.clip(audio.T, -1.0, 1.0)
    sf.write(str(path), clipped, sample_rate, subtype="PCM_16")


def duration(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> float:
    return audio.shape[-1] / sample_rate

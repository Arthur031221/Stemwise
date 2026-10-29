"""Shared fixtures. Fast tests use a stub separator and a stub beat tracker, no model downloads."""

from __future__ import annotations

import time

import numpy as np
import pytest
import soundfile as sf
from starlette.testclient import TestClient

from stemwise import beats, library, pipeline
from stemwise.audio import SAMPLE_RATE
from stemwise.server import create_app

TRIADS = {"C": (0, 4, 7), "Am": (9, 0, 4), "F": (5, 9, 0), "G": (7, 11, 2)}


def triad(root_offsets: tuple[int, ...], seconds: float) -> np.ndarray:
    """A plucked-sounding chord: three notes with a few harmonics, around middle C."""
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    out = np.zeros_like(t)
    for semitone in root_offsets:
        f0 = 261.63 * 2 ** (semitone / 12)
        for h, amp in enumerate((1.0, 0.5, 0.3, 0.15), start=1):
            out += amp * np.sin(2 * np.pi * f0 * h * t)
    return (out / np.abs(out).max() * 0.5).astype(np.float32)


def progression(names: list[str], seconds_each: float = 2.0) -> np.ndarray:
    return np.concatenate([triad(TRIADS[n], seconds_each) for n in names])


@pytest.fixture
def song_wav(tmp_path):
    """Eight seconds of C Am F G, written as a WAV file."""
    mono = progression(["C", "Am", "F", "G"])
    path = tmp_path / "Practice Tune.wav"
    sf.write(path, np.stack([mono, mono], axis=1), SAMPLE_RATE)
    return path


class StubSeparator:
    """Splits a mix by gain only: fast, deterministic, and still exercises the whole pipeline."""

    device = "cpu"

    def split(self, audio, progress=None):
        weights = {"vocals": 0.0, "drums": 0.1, "bass": 0.2, "guitar": 0.5, "piano": 0.2, "other": 0.0}
        for step in range(1, 4):
            if progress:
                progress(step / 3)
        return {name: (audio * w).astype(np.float32) for name, w in weights.items()}


@pytest.fixture(autouse=True)
def stub_beats(monkeypatch, request):
    if request.node.get_closest_marker("slow"):
        return

    def fake_track(mono, device="cpu"):
        seconds = len(mono) / SAMPLE_RATE
        grid = [round(i * 0.5, 3) for i in range(int(seconds / 0.5))]
        return beats.BeatMap(beats=grid, downbeats=grid[::4])

    monkeypatch.setattr(beats, "track", fake_track)
    monkeypatch.setattr(pipeline.beats, "track", fake_track)


@pytest.fixture
def lib(tmp_path):
    return library.Library(tmp_path / "library")


@pytest.fixture
def client(lib):
    app = create_app(lib, separator=StubSeparator())
    with TestClient(app, base_url="http://localhost") as c:
        yield c
    app.state.jobs.close()


def wait_ready(client: TestClient, song_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        meta = client.get(f"/api/songs/{song_id}").json()
        if meta["status"] in ("ready", "error"):
            return meta
        time.sleep(0.05)
    raise AssertionError("song did not finish processing")


@pytest.fixture
def ready_song(client, song_wav):
    res = client.post("/api/songs", params={"name": song_wav.name}, content=song_wav.read_bytes())
    assert res.status_code == 202
    song_id = res.json()["id"]
    meta = wait_ready(client, song_id)
    assert meta["status"] == "ready", meta
    return song_id, meta

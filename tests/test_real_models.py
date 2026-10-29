"""Runs the real Demucs and beat_this models. Deselect with: pytest -m 'not slow'."""

import numpy as np
import pytest

from stemwise import audio, beats
from stemwise.pipeline import analyse
from stemwise.separate import STEMS, Separator

pytestmark = pytest.mark.slow


def click_track(seconds=10.0, bpm=120.0):
    rate = audio.SAMPLE_RATE
    out = np.zeros(int(seconds * rate), dtype=np.float32)
    t = np.arange(int(0.05 * rate)) / rate
    tick = np.sin(2 * np.pi * 220 * t) * np.exp(-t * 60)
    for beat in np.arange(0, seconds - 0.1, 60 / bpm):
        i = int(beat * rate)
        out[i : i + len(tick)] += tick * (1.0 if round(beat / (60 / bpm)) % 4 == 0 else 0.6)
    return out


def test_pipeline_end_to_end_with_real_models(tmp_path):
    import soundfile as sf

    mono = click_track()
    source = tmp_path / "clicks.wav"
    sf.write(source, np.stack([mono, mono], axis=1), audio.SAMPLE_RATE)
    stems_dir = tmp_path / "stems"
    result = analyse(source, stems_dir, Separator(), lambda stage, fraction: None)
    assert sorted(p.stem for p in stems_dir.glob("*.flac")) == sorted(STEMS)
    assert result["duration"] == pytest.approx(10.0, abs=0.05)
    assert result["bpm"] == pytest.approx(120.0, abs=3.0)
    assert len(result["downbeats"]) >= 2


def test_stems_add_back_up_to_the_mix(tmp_path):
    rng = np.random.default_rng(1)
    mix = (rng.standard_normal((2, audio.SAMPLE_RATE * 6)) * 0.1).astype(np.float32)
    stems = Separator().split(mix)
    total = sum(stems.values())
    error = np.sqrt(np.mean((total - mix) ** 2)) / np.sqrt(np.mean(mix**2))
    assert error < 0.2


def test_beat_tracker_finds_a_steady_click():
    assert beats.track.__module__ == "stemwise.beats", "the stub must not leak into slow tests"
    result = beats.track(click_track(), "cpu")
    assert result.bpm == pytest.approx(120.0, abs=3.0)

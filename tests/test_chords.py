import numpy as np

from stemwise import chords

from .conftest import SAMPLE_RATE, progression, triad


def as_stems(mono):
    stereo = np.stack([mono, mono]).astype(np.float32)
    return {"guitar": stereo}


def test_detects_each_triad():
    stems = as_stems(progression(["C", "Am", "F", "G"]))
    beats = [i * 0.5 for i in range(16)]
    sequence = chords.detect(stems, beats)
    labels = [c.label for c in sequence]
    assert labels == ["C", "Am", "F", "G"]
    assert [round(c.start) for c in sequence] == [0, 2, 4, 6]


def test_chords_are_contiguous_and_cover_the_song():
    stems = as_stems(progression(["C", "G"], 3.0))
    sequence = chords.detect(stems, [i * 0.5 for i in range(12)])
    assert sequence[0].start == 0
    for a, b in zip(sequence, sequence[1:], strict=False):
        assert abs(a.end - b.start) < 1e-6
    assert abs(sequence[-1].end - 6.0) < 0.6


def test_silence_is_no_chord():
    stems = {"guitar": np.zeros((2, SAMPLE_RATE * 3), dtype=np.float32)}
    sequence = chords.detect(stems, [i * 0.5 for i in range(6)])
    assert {c.label for c in sequence} == {"N"}


def test_key_of_a_major_progression():
    stems = as_stems(progression(["C", "Am", "F", "G", "C"], 2.0))
    assert chords.estimate_key(stems) == "C major"


def test_key_of_a_minor_progression():
    mono = np.concatenate([triad((9, 0, 4), 3), triad((2, 5, 9), 2), triad((4, 8, 11), 3), triad((9, 0, 4), 3)])
    assert chords.estimate_key(as_stems(mono)).endswith("minor")


def test_label_names():
    assert chords.label_of(9, "min") == "Am"
    assert chords.label_of(7, "7") == "G7"
    assert chords.label_of(2, "min7") == "Dm7"

"""Chord and beat accuracy on GuitarSet (Xi et al. 2018, CC BY 4.0), scored with mir_eval.

Download audio_mono-mic.zip and annotation.zip from https://zenodo.org/records/3371780,
unpack both into one folder, then:

    python bench/chords_guitarset.py DIR --cache cache.pkl

Every clip runs the same path the app uses: separate, track beats, detect chords.
Reference labels come from the "instructed" chord annotation (maj, min, 7, hdim7).
"""

from __future__ import annotations

import argparse
import json
import pickle
import warnings
from pathlib import Path

import mir_eval
import numpy as np

from stemwise import audio, beats, chords
from stemwise.separate import Separator


def reference(jams_path: Path) -> tuple[np.ndarray, list[str], np.ndarray, float]:
    data = json.loads(jams_path.read_text())
    chord_ann = [a for a in data["annotations"] if a["namespace"] == "chord"]
    instructed = next(a for a in chord_ann if not a["annotation_metadata"].get("data_source"))
    rows = instructed["data"]
    intervals = np.array([[r["time"], r["time"] + r["duration"]] for r in rows])
    beat_rows = next(a for a in data["annotations"] if a["namespace"] == "beat_position")["data"]
    ref_beats = np.array([r["time"] for r in beat_rows])
    ref_downbeats = np.array([r["time"] for r in beat_rows if r["value"]["position"] == 1])
    return intervals, [r["value"] for r in rows], ref_beats, ref_downbeats, data["file_metadata"]["duration"]


def to_mir_eval(label: str) -> str:
    if label == "N":
        return "N"
    root, quality = (label[:2], label[2:]) if label[1:2] == "#" else (label[:1], label[1:])
    return f"{root}:{ {'': 'maj', 'm': 'min', 'm7': 'min7'}.get(quality, quality) }"


def features_for(folder: Path, name: str, separator: Separator) -> dict:
    mix = audio.decode(folder / f"{name}_mic.wav")
    stems = separator.split(mix)
    track = beats.track(audio.decode(folder / f"{name}_mic.wav", mono=True)[0], separator.device)
    return {"feat": chords.extract(stems), "beats": track}


def score(cache: dict, folder: Path, **params) -> dict:
    totals: dict[str, list[float]] = {}
    weights = []
    f_beat, f_down = [], []
    for name, item in cache.items():
        ref_i, ref_l, ref_b, ref_d, dur = reference(folder / f"{name}.jams")
        est = chords.decode(item["feat"], item["beats"].beats, **params)
        est_i = np.array([[c.start, c.end] for c in est])
        est_l = [to_mir_eval(c.label) for c in est]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            no_chord = mir_eval.chord.NO_CHORD
            ref_i, ref_l = mir_eval.util.adjust_intervals(ref_i, ref_l, 0.0, dur, no_chord, no_chord)
            est_i, est_l = mir_eval.util.adjust_intervals(est_i, est_l, 0.0, dur, no_chord, no_chord)
            result = mir_eval.chord.evaluate(ref_i, ref_l, est_i, est_l)
        weights.append(dur)
        for key in ("root", "majmin", "triads", "sevenths"):
            totals.setdefault(key, []).append(result[key])
        trim = mir_eval.beat.trim_beats
        f_beat.append(mir_eval.beat.f_measure(trim(ref_b), trim(np.array(item["beats"].beats))))
        f_down.append(mir_eval.beat.f_measure(trim(ref_d), trim(np.array(item["beats"].downbeats))))
    out = {k: round(float(np.average(v, weights=weights)), 3) for k, v in totals.items()}
    out["beat_f"] = round(float(np.mean(f_beat)), 3)
    out["downbeat_f"] = round(float(np.mean(f_down)), 3)
    out["clips"] = len(weights)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--cache", type=Path, default=Path("guitarset-features.pkl"))
    ap.add_argument("--params", default="{}", help="JSON keyword arguments for chords.decode")
    args = ap.parse_args()

    names = sorted(p.stem for p in args.folder.glob("*.jams"))
    cache = pickle.loads(args.cache.read_bytes()) if args.cache.exists() else {}
    separator = Separator()
    for i, name in enumerate(names):
        if name not in cache:
            cache[name] = features_for(args.folder, name, separator)
            if i % 20 == 0:
                print(f"{i + 1}/{len(names)}", flush=True)
    args.cache.write_bytes(pickle.dumps(cache))

    params = json.loads(args.params)
    # constants were tuned on every fifth clip, so report on the other four fifths
    held_out = {n: cache[n] for i, n in enumerate(names) if i % 5 != 0}
    report = {
        "held_out_all": score(held_out, args.folder, **params),
        "held_out_comp": score({n: v for n, v in held_out.items() if "_comp" in n}, args.folder, **params),
        "held_out_solo": score({n: v for n, v in held_out.items() if "_solo" in n}, args.folder, **params),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

"""Build the static demo that GitHub Pages serves.

Cuts an excerpt from a licensed song, runs the real Stemwise pipeline on it, and writes
small AAC stems plus the analysis next to the web app. Needs the GPU or CPU extras and ffmpeg.

    python scripts/build_demo.py song.mp3 --start 20 --seconds 36 --out web/demo
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from stemwise.pipeline import analyse
from stemwise.separate import Separator

CREDIT = {
    "title": "Surf Shimmy",
    "artist": "Kevin MacLeod",
    "url": "https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1700018",
    "license": "CC BY 4.0",
}


def run(*cmd: str) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source")
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--seconds", type=float, default=36.0)
    parser.add_argument("--out", default="web/demo")
    parser.add_argument("--slug", default="surf-shimmy")
    parser.add_argument("--title", default="Surf Shimmy (36 s excerpt)")
    parser.add_argument("--bitrate", default="112k")
    args = parser.parse_args()

    out = Path(args.out) / args.slug
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=Path(args.out)) as tmp:
        clip = Path(tmp) / "clip.wav"
        run(
            "ffmpeg",
            "-y",
            "-ss",
            str(args.start),
            "-t",
            str(args.seconds),
            "-i",
            args.source,
            "-ar",
            "44100",
            "-ac",
            "2",
            str(clip),
        )
        stems_dir = Path(tmp) / "stems"
        result = analyse(clip, stems_dir, Separator(), lambda stage, f: print(f"\r{stage:<11}{f * 100:4.0f}%", end=""))
        print()
        for flac in sorted(stems_dir.glob("*.flac")):
            run(
                "ffmpeg",
                "-y",
                "-i",
                str(flac),
                "-c:a",
                "aac",
                "-b:a",
                args.bitrate,
                "-movflags",
                "+faststart",
                str(out / f"{flac.stem}.m4a"),
            )

    meta = {
        "id": args.slug,
        "title": args.title,
        "status": "ready",
        "stage": "ready",
        "progress": 1.0,
        "credit": CREDIT,
        **{k: v for k, v in result.items() if k not in ("timings", "device")},
    }
    (out / "meta.json").write_text(json.dumps(meta, separators=(",", ":")))
    index = [{k: meta[k] for k in ("id", "title", "status", "stage", "progress", "duration", "bpm", "key")}]
    (Path(args.out) / "index.json").write_text(json.dumps(index))
    size = sum(f.stat().st_size for f in out.iterdir())
    print(
        f"{args.slug}: {meta['duration']}s, {meta['bpm']} BPM, {meta['key']}, {len(meta['chords'])} chords, "
        f"{size / 1e6:.1f} MB"
    )


if __name__ == "__main__":
    main()

"""Command line entry point: serve, split, bench, doctor."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
import webbrowser
from pathlib import Path

from . import __version__


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .library import Library
    from .server import create_app

    if args.host in ("0.0.0.0", "::"):
        print("Bind to one address instead, for example --host 192.168.1.20. Stemwise has no login.", file=sys.stderr)
        return 2
    library = Library(Path(args.library) if args.library else None)
    app = create_app(library, extra_hosts={args.host} if args.host not in ("127.0.0.1", "localhost") else set())
    url = f"http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{args.port}"
    print(f"Stemwise {__version__} is running at {url}  (library: {library.root.parent})")
    if not args.no_open:
        webbrowser.open(url)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def _need_ffmpeg() -> bool:
    if shutil.which("ffmpeg"):
        return True
    print("ffmpeg was not found. Install it first: https://ffmpeg.org/download.html", file=sys.stderr)
    return False


def cmd_split(args: argparse.Namespace) -> int:
    from . import audio, export
    from .pipeline import analyse
    from .separate import Separator

    if not _need_ffmpeg():
        return 2
    source = Path(args.file)
    if not source.is_file():
        print(f"no such file: {source}", file=sys.stderr)
        return 2
    out = Path(args.output) if args.output else source.with_suffix("").parent / f"{source.stem} stems"
    separator = Separator(args.device)

    def report(stage: str, fraction: float) -> None:
        print(f"\r{stage:<11}{fraction * 100:5.0f}%", end="", file=sys.stderr, flush=True)

    try:
        result = analyse(source, out, separator, report)
    except audio.AudioError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1
    print(file=sys.stderr)
    if args.format == "wav":
        for flac in list(out.glob("*.flac")):
            audio.write(flac.with_suffix(".wav"), export.read_stem(flac))
            flac.unlink()
    meta = {"title": source.stem, **result}
    (out / "chords.txt").write_text(export.chord_sheet_text(meta))
    try:
        (out / "beats.mid").write_bytes(export.beats_midi(meta))
    except ValueError as exc:
        print(f"no beats.mid: {exc}", file=sys.stderr)
    print(
        f"{source.name}: {result['duration']:.0f}s, {result['bpm']} BPM, {result['key']}, "
        f"{len(result['chords'])} chords, on {result['device']}"
    )
    print(f"separation {result['timings']['separate']}s. Wrote {out}")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    from . import audio
    from .separate import Separator

    if not _need_ffmpeg():
        return 2
    mix = audio.decode(args.file)
    seconds = audio.duration(mix)
    separator = Separator(args.device, half=args.fp16)
    _ = separator.model  # load outside the timed region
    runs = []
    for _ in range(args.runs + 1):
        start = time.perf_counter()
        separator.split(mix)
        if separator.device == "cuda":
            import torch

            torch.cuda.synchronize()
        runs.append(time.perf_counter() - start)
    best = min(runs[1:])  # the first run warms up kernels
    print(
        f"device {separator.device}  audio {seconds:.1f}s  separation {best:.2f}s  "
        f"{seconds / best:.1f}x realtime  (best of {args.runs} after one warm-up)"
    )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    import torch

    ok = True
    print(f"stemwise {__version__}, python {sys.version.split()[0]}, torch {torch.__version__}")
    ffmpeg = shutil.which("ffmpeg")
    print(f"ffmpeg   {'ok: ' + ffmpeg if ffmpeg else 'MISSING, install from https://ffmpeg.org/download.html'}")
    ok &= bool(ffmpeg)
    if torch.cuda.is_available():
        print(f"device   cuda: {torch.cuda.get_device_name(0)}")
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        print("device   mps (Apple GPU)")
    else:
        print("device   cpu only: a 4 minute song takes a minute or more to separate")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stemwise", description="A local practice studio for musicians.")
    parser.add_argument("--version", action="version", version=f"stemwise {__version__}")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="open the practice studio in your browser (default)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--library", help="where songs are stored (default: the user data folder)")
    serve.add_argument("--no-open", action="store_true", help="do not open a browser tab")
    serve.set_defaults(func=cmd_serve)

    split = sub.add_parser("split", help="split a file into stems and write chords and beats")
    split.add_argument("file")
    split.add_argument("-o", "--output", help="output folder (default: a '<name> stems' folder next to the file)")
    split.add_argument("--format", choices=["flac", "wav"], default="flac")
    split.add_argument("--device", help="cuda, mps or cpu (default: best available)")
    split.set_defaults(func=cmd_split)

    bench = sub.add_parser("bench", help="time stem separation on a file")
    bench.add_argument("file")
    bench.add_argument("--runs", type=int, default=3)
    bench.add_argument("--device")
    bench.add_argument("--fp16", action="store_true", help="mixed precision, faster but not identical")
    bench.set_defaults(func=cmd_bench)

    doctor = sub.add_parser("doctor", help="check ffmpeg and the compute device")
    doctor.set_defaults(func=cmd_doctor)

    words = sys.argv[1:] if argv is None else list(argv)
    if not words or (words[0].startswith("-") and words[0] not in ("-h", "--help", "--version")):
        words.insert(0, "serve")  # bare `stemwise --port 9000` means `stemwise serve --port 9000`
    args = parser.parse_args(words)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

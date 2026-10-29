"""Record the README demo: drive the live demo page in Chrome and turn the video into assets/demo.gif.

    python scripts/record_demo.py            # needs Chrome and ffmpeg

The interaction is real: the page plays the bundled song through the same audio engine as the app.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import subprocess
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SIZE = {"width": 1280, "height": 900}


def serve(directory: Path) -> http.server.ThreadingHTTPServer:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(directory)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def drag(page, duration: float, start: float, end: float) -> None:
    box = page.locator("#timeline").bounding_box()
    y = box["y"] + 10
    page.mouse.move(box["x"] + box["width"] * start / duration, y)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * end / duration, y, steps=12)
    page.mouse.up()


def perform(page, url: str, meta: dict) -> None:
    page.goto(url)
    page.wait_for_selector("#studio:not([hidden])", timeout=30000)
    page.wait_for_timeout(1200)
    page.click("#play")  # the whole song, all six stems
    page.wait_for_timeout(2600)
    page.keyboard.press("2")  # mute the drums
    page.wait_for_timeout(1400)
    page.keyboard.press("2")
    bars = meta["downbeats"]
    drag(page, meta["duration"], bars[8] + 0.2, bars[9] + 0.2)  # loop one bar
    page.wait_for_timeout(1500)
    page.click("#tempo-presets button:text('70%')")
    page.wait_for_timeout(3600)
    page.keyboard.press("c")  # click track
    page.wait_for_timeout(2400)
    page.keyboard.press("ArrowUp")  # transpose
    page.keyboard.press("ArrowUp")
    page.wait_for_timeout(2400)
    page.click("#play")
    page.wait_for_timeout(500)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "assets" / "demo.gif")
    ap.add_argument("--channel", default="chrome")
    args = ap.parse_args()

    web = ROOT / "web"
    index = json.loads((web / "demo" / "index.json").read_text())
    entry = index[0] if isinstance(index, list) else index["songs"][0]
    slug = entry["id"] if isinstance(entry, dict) else entry
    meta = json.loads((web / "demo" / slug / "meta.json").read_text())

    httpd = serve(web)
    url = f"http://localhost:{httpd.server_address[1]}/?demo"
    with tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir())) as tmp, sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, args=["--autoplay-policy=no-user-gesture-required"])
        context = browser.new_context(viewport=SIZE, record_video_dir=tmp, record_video_size=SIZE)
        page = context.new_page()
        perform(page, url, meta)
        context.close()
        browser.close()
        video = next(Path(tmp).glob("*.webm"))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        palette = Path(tmp) / "palette.png"
        scale = "fps=12,scale=960:-1:flags=lanczos"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", f"{scale},palettegen=max_colors=96", str(palette)],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(video),
                "-i",
                str(palette),
                "-lavfi",
                f"{scale}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4",
                str(args.out),
            ],
            check=True,
        )
    httpd.shutdown()
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()

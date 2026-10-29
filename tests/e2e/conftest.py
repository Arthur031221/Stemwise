"""Browser fixtures: the static demo behind a plain file server, and the real server with a stub separator."""

from __future__ import annotations

import functools
import http.server
import json
import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from stemwise.server import create_app

from ..conftest import StubSeparator

WEB = Path(__file__).resolve().parents[2] / "web"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def demo_url():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(WEB))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", free_port()), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://localhost:{httpd.server_address[1]}/?demo"
    httpd.shutdown()


@pytest.fixture
def server_url(tmp_path):
    from stemwise.library import Library

    port = free_port()
    app = create_app(Library(tmp_path / "library"), separator=StubSeparator())
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://localhost:{port}/"
    server.should_exit = True
    thread.join(timeout=5)
    app.state.jobs.close()


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright

    channel = os.environ.get("STEMWISE_BROWSER_CHANNEL")
    with sync_playwright() as p:
        args = ["--autoplay-policy=no-user-gesture-required"]
        try:
            b = p.chromium.launch(channel=channel, args=args) if channel else p.chromium.launch(args=args)
        except Exception:
            b = p.chromium.launch(channel="chrome", args=args)
        yield b
        b.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1360, "height": 900})
    page = context.new_page()
    page.problems = []
    page.on("pageerror", lambda e: page.problems.append(f"pageerror: {e}"))
    page.on(
        "console",
        lambda m: page.problems.append(f"console {m.type}: {m.text}") if m.type == "error" else None,
    )
    yield page
    context.close()


@pytest.fixture(scope="session")
def demo_meta():
    return json.loads((WEB / "demo" / "surf-shimmy" / "meta.json").read_text())

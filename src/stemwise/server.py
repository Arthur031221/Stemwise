"""The local web server: a small JSON API, stem files, exports and the static player."""

from __future__ import annotations

import json
import re
import urllib.parse
import uuid
from pathlib import Path

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import __version__, export
from .jobs import JobQueue
from .library import Library, hash_file
from .separate import STEMS, Separator

MAX_UPLOAD = 1 << 30  # 1 GiB
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}
SAFE_NAME = re.compile(r"[^\w .,'()&+-]+", re.UNICODE)


def web_root() -> Path:
    packaged = Path(__file__).parent / "web"
    return packaged if packaged.is_dir() else Path(__file__).resolve().parents[2] / "web"


def hostname(host_header: str) -> str:
    """Strip the port from a Host header value, keeping bracketed IPv6 literals intact."""
    if host_header.startswith("["):
        return host_header.split("]")[0] + "]"
    return host_header.rsplit(":", 1)[0] if ":" in host_header else host_header


class LocalOnly:
    """Reject requests whose Host or Origin is not this machine (DNS rebinding, cross-site writes)."""

    def __init__(self, app, extra_hosts: set[str]):
        self.app = app
        self.allowed = LOCAL_HOSTS | extra_hosts

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
            raw_host = headers.get("host", "")
            origin = headers.get("origin")
            bad_origin = origin is not None and origin.split("://", 1)[-1] != raw_host
            if hostname(raw_host) not in self.allowed or bad_origin:
                response = JSONResponse({"error": "forbidden host"}, status_code=403)
                return await response(scope, receive, send)
        return await self.app(scope, receive, send)


def clean_text(text: str) -> str:
    """Keep a title readable and safe to drop into a file name or an HTML page."""
    return SAFE_NAME.sub("", text).strip()[:120] or "Untitled"


def clean_title(filename: str) -> str:
    return clean_text(Path(filename).stem)


def create_app(
    library: Library | None = None,
    separator: Separator | None = None,
    extra_hosts: set[str] | None = None,
    start_worker: bool = True,
) -> Starlette:
    library = library or Library()
    jobs = JobQueue(library, separator) if start_worker else None
    for song in library.listing():
        if song["status"] in ("queued", "processing"):
            meta = library.read(song["id"])
            meta.update(status="error", stage="error", error="Interrupted. Add the file again.")
            library.write(song["id"], meta)
            for leftover in library.folder(song["id"]).glob("source.*"):
                leftover.unlink(missing_ok=True)

    def song_or_404(song_id: str) -> dict:
        if not library.exists(song_id):
            raise HTTPException(404, "no such song")
        return library.read(song_id)

    async def health(request: Request) -> Response:
        sep = jobs.separator if jobs else None
        return JSONResponse(
            {
                "version": __version__,
                "device": sep.device if sep else None,
                "stems": list(STEMS),
            }
        )

    async def list_songs(request: Request) -> Response:
        return JSONResponse(library.listing())

    async def upload(request: Request) -> Response:
        name = request.query_params.get("name", "Untitled")
        tmp = library.root / f".upload-{uuid.uuid4().hex}"
        size = 0
        try:
            with open(tmp, "wb") as fh:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > MAX_UPLOAD:
                        raise HTTPException(413, "file is larger than 1 GiB")
                    fh.write(chunk)
            if size == 0:
                raise HTTPException(400, "empty upload")
            song_id = await run_in_threadpool(hash_file, tmp)
            if library.exists(song_id) and library.read(song_id)["status"] in ("ready", "queued", "processing"):
                return JSONResponse({"id": song_id, "existing": True})
            library.create(song_id, clean_title(name), name)
            kept = library.folder(song_id) / f"source{Path(name).suffix[:8].lower()}"
            tmp.replace(kept)
        finally:
            tmp.unlink(missing_ok=True)
        if jobs is None:
            return JSONResponse({"id": song_id, "existing": False})
        jobs.submit(song_id, kept)
        return JSONResponse({"id": song_id, "existing": False}, status_code=202)

    async def get_song(request: Request) -> Response:
        return JSONResponse(song_or_404(request.path_params["song_id"]))

    async def delete_song(request: Request) -> Response:
        song_or_404(request.path_params["song_id"])
        library.delete(request.path_params["song_id"])
        return Response(status_code=204)

    async def rename_song(request: Request) -> Response:
        meta = song_or_404(request.path_params["song_id"])
        body = await request.json()
        meta["title"] = clean_text(str(body.get("title", meta["title"])))
        library.write(meta["id"], meta)
        return JSONResponse({"title": meta["title"]})

    async def stem_file(request: Request) -> Response:
        song_id, stem = request.path_params["song_id"], request.path_params["stem"]
        song_or_404(song_id)
        if stem not in STEMS:
            raise HTTPException(404, "no such stem")
        path = library.stem_path(song_id, stem)
        if not path.is_file():
            raise HTTPException(404, "stem is not ready")
        return FileResponse(path, media_type="audio/flac")

    async def export_file(request: Request) -> Response:
        song_id, kind = request.path_params["song_id"], request.path_params["kind"]
        meta = song_or_404(song_id)
        if meta["status"] != "ready":
            raise HTTPException(409, "song is still processing")
        title = meta["title"]
        leave_out = [s for s in request.query_params.get("without", "").split(",") if s in STEMS]
        fmt = "flac" if request.query_params.get("format") == "flac" else "wav"

        def build() -> tuple[bytes, str, str]:
            if kind == "backing":
                return (
                    export.backing_track(library, song_id, leave_out, fmt),
                    f"audio/{fmt}",
                    f"{title} - backing.{fmt}",
                )
            if kind == "stems":
                return export.stems_zip(library, song_id), "application/zip", f"{title} - stems.zip"
            if kind == "chords.txt":
                return export.chord_sheet_text(meta).encode(), "text/plain; charset=utf-8", f"{title} - chords.txt"
            if kind == "chords.html":
                return export.chord_sheet_html(meta).encode(), "text/html; charset=utf-8", f"{title} - chords.html"
            if kind == "beats.mid":
                return export.beats_midi(meta), "audio/midi", f"{title} - beats.mid"
            raise HTTPException(404, "unknown export")

        try:
            body, mime, fname = await run_in_threadpool(build)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        ascii_name = json.dumps(fname.encode("ascii", "replace").decode())
        disposition = f"attachment; filename={ascii_name}; filename*=UTF-8''{urllib.parse.quote(fname)}"
        return Response(body, media_type=mime, headers={"Content-Disposition": disposition})

    routes = [
        Route("/api/health", health),
        Route("/api/songs", list_songs, methods=["GET"]),
        Route("/api/songs", upload, methods=["POST"]),
        Route("/api/songs/{song_id}", get_song, methods=["GET"]),
        Route("/api/songs/{song_id}", delete_song, methods=["DELETE"]),
        Route("/api/songs/{song_id}", rename_song, methods=["PATCH"]),
        Route("/api/songs/{song_id}/stems/{stem}.flac", stem_file),
        Route("/api/songs/{song_id}/export/{kind}", export_file),
        Mount("/", StaticFiles(directory=web_root(), html=True), name="web"),
    ]
    app = Starlette(routes=routes, middleware=[Middleware(LocalOnly, extra_hosts=extra_hosts or set())])
    app.state.library, app.state.jobs = library, jobs
    return app

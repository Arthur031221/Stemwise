"""On-disk song library. One folder per song, named by the hash of the uploaded bytes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

SAFE_ID_LEN = 12


def home() -> Path:
    env = os.environ.get("STEMWISE_HOME")
    if env:
        return Path(env).expanduser()
    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / "stemwise"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "stemwise"
    return Path.home() / ".local" / "share" / "stemwise"


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()[:SAFE_ID_LEN]


def valid_id(song_id: str) -> bool:
    return len(song_id) == SAFE_ID_LEN and all(c in "0123456789abcdef" for c in song_id)


class Library:
    def __init__(self, root: Path | None = None):
        self.root = (root or home()) / "songs"
        self.root.mkdir(parents=True, exist_ok=True)

    def folder(self, song_id: str) -> Path:
        if not valid_id(song_id):
            raise KeyError(song_id)
        return self.root / song_id

    def exists(self, song_id: str) -> bool:
        return valid_id(song_id) and (self.folder(song_id) / "meta.json").is_file()

    def read(self, song_id: str) -> dict:
        if not self.exists(song_id):
            raise KeyError(song_id)
        return json.loads((self.folder(song_id) / "meta.json").read_text())

    def write(self, song_id: str, meta: dict) -> None:
        folder = self.folder(song_id)
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / "meta.json.tmp"
        tmp.write_text(json.dumps(meta, indent=1))
        tmp.replace(folder / "meta.json")

    def create(self, song_id: str, title: str, source_name: str) -> dict:
        meta = {
            "id": song_id,
            "title": title,
            "source": source_name,
            "status": "queued",
            "stage": "queued",
            "progress": 0.0,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        self.write(song_id, meta)
        return meta

    def listing(self) -> list[dict]:
        songs = []
        for entry in sorted(self.root.iterdir()):
            if valid_id(entry.name) and (entry / "meta.json").is_file():
                meta = json.loads((entry / "meta.json").read_text())
                songs.append(
                    {
                        k: meta.get(k)
                        for k in (
                            "id",
                            "title",
                            "status",
                            "stage",
                            "progress",
                            "duration",
                            "bpm",
                            "key",
                            "created",
                        )
                    }
                )
        return sorted(songs, key=lambda s: s.get("created") or "", reverse=True)

    def delete(self, song_id: str) -> None:
        shutil.rmtree(self.folder(song_id), ignore_errors=True)

    def stem_path(self, song_id: str, stem: str) -> Path:
        return self.folder(song_id) / "stems" / f"{stem}.flac"

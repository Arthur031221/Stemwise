"""A single worker thread. One song at a time keeps the GPU memory predictable."""

from __future__ import annotations

import queue
import threading
from pathlib import Path

from .library import Library
from .pipeline import run_job
from .separate import Separator


class JobQueue:
    def __init__(self, library: Library, separator: Separator | None = None):
        self.library = library
        self.separator = separator or Separator()
        self._queue: queue.Queue[tuple[str, Path] | None] = queue.Queue()
        self._thread = threading.Thread(target=self._work, name="stemwise-worker", daemon=True)
        self._thread.start()

    def submit(self, song_id: str, source: Path) -> None:
        self._queue.put((song_id, source))

    def _work(self) -> None:
        while (item := self._queue.get()) is not None:
            song_id, source = item
            try:
                run_job(self.library, song_id, source, self.separator)
            except Exception:  # run_job reports its own failures, this keeps the worker alive whatever happens
                pass
            finally:
                source.unlink(missing_ok=True)

    def close(self) -> None:
        self._queue.put(None)
        self._thread.join(timeout=5)

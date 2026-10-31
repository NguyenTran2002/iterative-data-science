"""Snapshot the notebook every time its content changes.

Polls from a thread in the runner process, outside the agent's context, so the
agent never learns it is being watched. Content that is not valid JSON (a file
caught mid-save) is skipped; the next poll picks up the finished file.
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path


class NotebookWatcher:
    def __init__(self, path: Path, snapshot_dir: Path, interval: float = 1.0):
        self.path = path
        self.snapshot_dir = snapshot_dir
        self.interval = interval
        self._last: bytes | None = None
        self._seq = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def poll_once(self) -> bool:
        try:
            content = self.path.read_bytes()
            json.loads(content)
        except (OSError, ValueError):
            return False
        if content == self._last:
            return False
        self._last = content
        self._seq += 1
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        (self.snapshot_dir / f"snap-{self._seq:04d}.ipynb").write_bytes(content)
        seen_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        with (self.snapshot_dir / "snapshots.jsonl").open("a") as f:
            f.write(json.dumps({"seq": self._seq, "seen_at": seen_at}) + "\n")
        return True

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self.poll_once()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join()
        self.poll_once()

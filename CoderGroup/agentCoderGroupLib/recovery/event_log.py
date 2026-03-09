from __future__ import annotations

import json
import threading
from pathlib import Path

from ..reporting.result_models import ProgressEvent


class TaskEventLog:
    def __init__(self, log_dir: str = "log"):
        self._events_dir = Path(log_dir) / "task_events"
        self._events_dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, threading.Lock] = {}
        self._meta_lock = threading.Lock()

    def _lock_for(self, task_id: str) -> threading.Lock:
        with self._meta_lock:
            lock = self._locks.get(task_id)
            if lock is None:
                lock = threading.Lock()
                self._locks[task_id] = lock
            return lock

    def append(self, task_id: str, event: dict) -> None:
        lock = self._lock_for(task_id)
        path = self._events_dir / f"{task_id}.jsonl"
        with lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def tail(self, task_id: str, n: int = 50) -> list[dict]:
        path = self._events_dir / f"{task_id}.jsonl"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []

        result: list[dict] = []
        for line in lines[-max(0, n) :]:
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result

    def append_progress_event(self, task_id: str, event: ProgressEvent) -> None:
        payload = {
            "event_type": event.event_type,
            "agent": event.agent,
            "message": event.message,
            "timestamp": event.timestamp,
            "data": event.data,
        }
        self.append(task_id, payload)
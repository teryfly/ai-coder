from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from .state_machine import InvalidStateTransitionError, TaskStateMachine
from .task_snapshot import TaskSnapshot


class TaskCheckpointStore:
    def __init__(self, log_dir: str = "log"):
        self._tasks_dir = Path(log_dir) / "tasks"
        self._events_dir = Path(log_dir) / "task_events"
        self._tasks_dir.mkdir(parents=True, exist_ok=True)
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

    def save(self, snapshot: TaskSnapshot) -> None:
        task_id = snapshot.task_id
        lock = self._lock_for(task_id)
        with lock:
            final_path = self._tasks_dir / f"{task_id}.json"
            tmp_path = self._tasks_dir / f"{task_id}.json.tmp"
            content = json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2)
            tmp_path.write_text(content, encoding="utf-8")
            os.replace(tmp_path, final_path)

    def load(self, task_id: str) -> TaskSnapshot | None:
        path = self._tasks_dir / f"{task_id}.json"
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        data = json.loads(raw)
        return TaskSnapshot.from_dict(data)

    def list_unfinished(self, source: str | None = None) -> list[TaskSnapshot]:
        snapshots: list[TaskSnapshot] = []
        for path in self._tasks_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                snap = TaskSnapshot.from_dict(data)
            except Exception:
                continue
            if snap.state == "done":
                continue
            if source and snap.source != source:
                continue
            snapshots.append(snap)

        snapshots.sort(key=lambda s: s.updated_at, reverse=True)
        return snapshots

    def get_latest_unfinished(self, source: str | None = None) -> TaskSnapshot | None:
        items = self.list_unfinished(source=source)
        return items[0] if items else None

    def mark_interrupted(self, task_id: str) -> None:
        snap = self.load(task_id)
        if snap is None:
            return
        if snap.state in {"done", "interrupted"}:
            return
        try:
            new_snap = TaskStateMachine.transition(snap, "interrupted")
        except InvalidStateTransitionError:
            return
        self.save(new_snap)

    def mark_all_interrupted_on_startup(self, source: str | None = None) -> None:
        unfinished = self.list_unfinished(source=source)
        for snap in unfinished:
            self.mark_interrupted(snap.task_id)
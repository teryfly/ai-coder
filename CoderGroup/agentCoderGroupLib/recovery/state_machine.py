from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Literal

from .task_snapshot import TaskSnapshot

TaskState = Literal["running", "waiting_input", "interrupted", "done", "error"]

VALID_TRANSITIONS: dict[str, set[str]] = {
    "running": {"waiting_input", "done", "error", "interrupted"},
    "waiting_input": {"running", "interrupted"},
    "interrupted": {"running"},
    "error": {"running", "interrupted"},
    "done": set(),
}


class InvalidStateTransitionError(Exception):
    pass


class TaskStateMachine:
    @staticmethod
    def transition(snapshot: TaskSnapshot, new_state: str) -> TaskSnapshot:
        current = snapshot.state
        allowed = VALID_TRANSITIONS.get(current, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid state transition: {current} -> {new_state}"
            )
        return replace(
            snapshot,
            state=new_state,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def mark_all_interrupted(snapshots: list[TaskSnapshot]) -> list[TaskSnapshot]:
        updated: list[TaskSnapshot] = []
        for snap in snapshots:
            if snap.state in {"done", "error"}:
                updated.append(snap)
                continue
            updated.append(TaskStateMachine.transition(snap, "interrupted"))
        return updated
from datetime import datetime, timezone
from typing import Callable, Literal

from .result_models import ProgressEvent


class ProgressReporter:
    def __init__(self, mode: Literal["console", "callback"] = "console"):
        self._mode = mode
        self._callbacks: list[Callable[[ProgressEvent], None]] = []

    def register_callback(self, cb: Callable[[ProgressEvent], None]) -> None:
        self._callbacks.append(cb)

    def emit(self, event_type: str, agent: str, message: str, data: dict = None) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        event = ProgressEvent(
            event_type=event_type,
            agent=agent,
            message=message,
            data=data,
            timestamp=ts,
        )
        if self._mode == "console":
            print(f"[{ts}] [{agent}] [{event_type}] {message}", flush=True)
        else:
            for cb in self._callbacks:
                cb(event)

    def emit_line_count(self, agent_name: str, reply: str) -> None:
        n = len(reply.splitlines())
        self.emit("output", agent_name, f"[{agent_name}] received {n} lines")

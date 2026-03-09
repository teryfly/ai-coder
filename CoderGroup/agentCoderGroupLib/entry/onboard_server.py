import threading
import uuid
from collections import deque
from typing import Optional

from ..adapters.chat_backend_client import ChatBackendClient
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..config.app_config import AppConfig
from ..config.task_types import normalize_task_type
from ..recovery import ResumeCoordinator, TaskCheckpointStore, TaskEventLog
from ..reporting.result_models import FinalResult, ProgressEvent
from .recoverable_task_runner import RecoverableTaskRunner


class _TaskState:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.state: str = "running"
        self.current_agent: str = ""
        self.message: str = ""
        self.progress_events: deque = deque(maxlen=200)
        self.result: Optional[FinalResult] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "state": self.state,
            "current_agent": self.current_agent,
            "message": self.message,
            "progress_events": list(self.progress_events),
        }


class OnboardServer:
    def __init__(self, config: AppConfig):
        self._config = config
        self._client = ChatBackendClient(config.chat_backend_url, config.chat_backend_token)
        self._tasks: dict[str, _TaskState] = {}
        self._lock = threading.Lock()

        self._store = TaskCheckpointStore(log_dir="log")
        self._event_log = TaskEventLog(log_dir="log")
        self._coordinator = ResumeCoordinator(self._store)
        self._runner = RecoverableTaskRunner(
            client=self._client,
            config=self._config,
            executor=CodeExecutorAdapter(),
            store=self._store,
            coordinator=self._coordinator,
            event_log=self._event_log,
        )
        self._store.mark_all_interrupted_on_startup(source="api")

    def _bind_status_callback(self, status: _TaskState):
        def progress_callback(event: ProgressEvent):
            status.current_agent = event.agent
            status.message = event.message
            status.progress_events.append(
                {
                    "event_type": event.event_type,
                    "agent": event.agent,
                    "message": event.message,
                    "timestamp": event.timestamp,
                    "data": event.data,
                }
            )
            if event.event_type == "user_input_required":
                status.state = "waiting_input"
            elif event.event_type == "complete":
                status.state = "done"
            elif event.event_type == "error":
                status.state = "error"

        return progress_callback

    def start_task(
        self,
        project_id: int,
        requirement: str,
        conv_name: str,
        task_type: str = "new_dev",
        project_document_ids: Optional[list[int]] = None,
        conversation_document_ids: Optional[list[int]] = None,
    ) -> str:
        task_id = str(uuid.uuid4())
        status = _TaskState(task_id)
        with self._lock:
            self._tasks[task_id] = status

        self._runner._pre_register_task_id(task_id)
        self._runner.start_task(
            project_id=project_id,
            requirement=requirement,
            conv_name=conv_name,
            task_type=normalize_task_type(task_type),
            source="api",
            project_document_ids=project_document_ids or [],
            conversation_document_ids=conversation_document_ids or [],
            progress_callback=self._bind_status_callback(status),
            predefined_task_id=task_id,
        )
        return task_id

    def resume_task(self, task_id: str, message: str | None = None) -> str:
        status = _TaskState(task_id)
        status.state = "running"
        with self._lock:
            self._tasks[task_id] = status

        resumed_task_id = self._runner.resume_task(
            task_id=task_id,
            progress_callback=self._bind_status_callback(status),
        )
        if message:
            self._runner.send_user_reply(task_id, message)
        return resumed_task_id

    def list_unfinished_tasks(self, source: str = "api") -> list[dict]:
        snapshots = self._coordinator.list_unfinished(source=source)
        items: list[dict] = []
        for s in snapshots:
            items.append(
                {
                    "task_id": s.task_id,
                    "source": s.source,
                    "project_id": s.project_id,
                    "conv_name": s.conv_name,
                    "task_type": s.task_type,
                    "state": s.state,
                    "current_stage": s.current_stage,
                    "requirement": (s.requirement[:200] + "...") if len(s.requirement) > 200 else s.requirement,
                    "updated_at": s.updated_at,
                }
            )
        return items

    def get_status(self, task_id: str) -> dict:
        with self._lock:
            status = self._tasks.get(task_id)
        if not status:
            raise KeyError(f"Task {task_id} not found")

        snap = self._store.load(task_id)
        if snap:
            status.state = snap.state
            status.current_agent = (snap.pending_user_input or {}).get("agent_name", status.current_agent)
            if snap.error_reason:
                status.message = snap.error_reason
        return status.to_dict()

    def send_user_reply(self, task_id: str, message: str) -> None:
        with self._lock:
            status = self._tasks.get(task_id)
        if not status:
            raise KeyError(f"Task {task_id} not found")
        self._runner.send_user_reply(task_id, message)
        status.state = "running"
        status.message = message

    def list_projects(self) -> list[dict]:
        return self._client.list_projects()

    def get_result(self, task_id: str) -> FinalResult:
        snap = self._store.load(task_id)
        if snap is None:
            raise KeyError(f"Task {task_id} not found")
        if snap.state not in {"done", "error"}:
            raise ValueError(f"Task {task_id} has no result yet (state={snap.state})")

        project_name = ""
        root_dir = "."
        if isinstance(snap.project, dict):
            project_name = str(snap.project.get("name", ""))
            root_dir = str(snap.project.get("ai_work_dir", "."))

        return FinalResult(
            task_id=task_id,
            success=snap.state == "done",
            root_dir=root_dir,
            project_name=project_name,
            sub_results=[],
            error_node=snap.error_node,
            error_reason=snap.error_reason,
        )

    def list_tasks(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "task_id": s.task_id,
                    "state": s.state,
                    "current_agent": s.current_agent,
                    "message": s.message,
                }
                for s in self._tasks.values()
            ]
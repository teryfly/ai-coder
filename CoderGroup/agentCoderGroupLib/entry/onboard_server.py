import threading
import uuid
from collections import deque
from typing import Optional

from ..adapters.chat_backend_client import ChatBackendClient
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..config.app_config import AppConfig
from ..config.task_types import normalize_task_type
from ..orchestrator.architect_loop import ArchitectLoop
from ..orchestrator.engineer_loop import EngineerLoop
from ..orchestrator.programmer_loop import ProgrammerLoop
from ..orchestrator.task_router import TaskRouter
from ..reporting.progress_reporter import ProgressReporter
from ..reporting.result_models import FinalResult, ProgressEvent


class _TaskState:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.state: str = "running"
        self.current_agent: str = ""
        self.message: str = ""
        self.progress_events: deque = deque(maxlen=200)
        self.result: Optional[FinalResult] = None
        self._input_event = threading.Event()
        self._user_reply: Optional[str] = None

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

        t = threading.Thread(
            target=self._run_task,
            args=(
                task_id,
                project_id,
                requirement,
                conv_name,
                normalize_task_type(task_type),
                project_document_ids or [],
                conversation_document_ids or [],
            ),
            daemon=True,
        )
        t.start()
        return task_id

    def _run_task(self, task_id: str, project_id: int, requirement: str, conv_name: str, task_type: str, project_doc_ids: list[int], conv_doc_ids: list[int]) -> None:
        status = self._tasks[task_id]

        def _cb(event: ProgressEvent):
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

        def _user_reply_provider(agent_name: str, latest_reply: str) -> str:
            status.current_agent = agent_name
            status.message = latest_reply
            status.state = "waiting_input"
            status._input_event.wait()
            status._input_event.clear()
            msg = (status._user_reply or "").strip()
            status._user_reply = None
            status.state = "running"
            return msg or "continue"

        reporter = ProgressReporter(mode="callback")
        reporter.register_callback(_cb)
        executor = CodeExecutorAdapter()

        try:
            project = self._client.get_project(project_id)

            if project_doc_ids:
                self._client.set_project_document_references(project_id, project_doc_ids)

            if task_type == "formal_dev":
                sub = EngineerLoop(self._client, self._config, executor, reporter).run(
                    requirement, project, _user_reply_provider, conv_doc_ids, conv_name
                )
                success = all(r.success for r in sub)
                failed = next((r for r in sub if not r.success), None)
                final = FinalResult(
                    task_id=task_id,
                    success=success,
                    root_dir=project.get("ai_work_dir", "."),
                    project_name=project.get("name", ""),
                    sub_results=sub,
                    error_node=failed.error_node if failed else None,
                    error_reason=failed.error_reason if failed else None,
                )
            elif task_type == "code_change":
                p = ProgrammerLoop(self._client, self._config, executor, reporter).run(
                    requirement, project, _user_reply_provider, conv_doc_ids, conv_name
                )
                final = FinalResult(
                    task_id=task_id,
                    success=p.success,
                    root_dir=p.root_dir,
                    project_name=project.get("name", ""),
                    sub_results=[],
                    error_node=p.error_node,
                    error_reason=p.error_reason,
                )
            else:
                docs = self._client.get_knowledge_docs(project_id)
                kb = "".join(
                    f"----- {d.get('filename', 'doc')} BEGIN -----\n{d.get('content', '')}\n----- {d.get('filename', 'doc')} END -----\n\n"
                    for d in docs
                )
                arch = ArchitectLoop(self._client, self._config, reporter).run(
                    project_id=project_id,
                    conv_name=conv_name,
                    first_message=(kb + requirement).strip(),
                    user_reply_provider=_user_reply_provider,
                    conversation_document_ids=conv_doc_ids,
                )
                route = TaskRouter(self._config.max_files_per_run).route(arch.file_count)
                reporter.emit("status", "TaskRouter", f"Routing to: {route}")
                if route == "programmer":
                    p = ProgrammerLoop(self._client, self._config, executor, reporter).run(
                        arch.task_doc, project, _user_reply_provider, conv_doc_ids
                    )
                    final = FinalResult(
                        task_id=task_id,
                        success=p.success,
                        root_dir=p.root_dir,
                        project_name=project.get("name", ""),
                        sub_results=[],
                        error_node=p.error_node,
                        error_reason=p.error_reason,
                    )
                else:
                    sub = EngineerLoop(self._client, self._config, executor, reporter).run(
                        arch.task_doc, project, _user_reply_provider, conv_doc_ids
                    )
                    success = all(r.success for r in sub)
                    failed = next((r for r in sub if not r.success), None)
                    final = FinalResult(
                        task_id=task_id,
                        success=success,
                        root_dir=project.get("ai_work_dir", "."),
                        project_name=project.get("name", ""),
                        sub_results=sub,
                        error_node=failed.error_node if failed else None,
                        error_reason=failed.error_reason if failed else None,
                    )

            status.result = final
            status.state = "done" if final.success else "error"
            reporter.emit("complete", "OnboardServer", f"Task finished: success={final.success}")

        except Exception as exc:
            status.state = "error"
            status.message = str(exc)
            reporter.emit("error", "OnboardServer", f"Task failed: {exc}")

    def get_status(self, task_id: str) -> dict:
        with self._lock:
            status = self._tasks.get(task_id)
        if not status:
            raise KeyError(f"Task {task_id} not found")
        return status.to_dict()

    def send_user_reply(self, task_id: str, message: str) -> None:
        with self._lock:
            status = self._tasks.get(task_id)
        if not status:
            raise KeyError(f"Task {task_id} not found")
        status._user_reply = message
        status._input_event.set()

    def list_projects(self) -> list[dict]:
        return self._client.list_projects()

    def get_result(self, task_id: str) -> FinalResult:
        with self._lock:
            status = self._tasks.get(task_id)
        if not status:
            raise KeyError(f"Task {task_id} not found")
        if not status.result:
            raise ValueError(f"Task {task_id} has no result yet (state={status.state})")
        return status.result

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
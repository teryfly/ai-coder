import threading
import uuid
from collections import deque
from typing import Optional

from ..adapters.chat_backend_client import ChatBackendClient
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..agents.architect_agent import ArchitectAgent
from ..config.app_config import AppConfig
from ..config.constants import GO_ON_PROMPT
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

    def start_task(self, project_id: int, requirement: str, conv_name: str) -> str:
        task_id = str(uuid.uuid4())
        status = _TaskState(task_id)
        with self._lock:
            self._tasks[task_id] = status
        t = threading.Thread(
            target=self._run_task,
            args=(task_id, project_id, requirement, conv_name),
            daemon=True,
        )
        t.start()
        return task_id

    def _run_task(
        self, task_id: str, project_id: int, requirement: str, conv_name: str
    ) -> None:
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
                status._input_event.wait()
                status._input_event.clear()
                status.state = "running"

        reporter = ProgressReporter(mode="callback")
        reporter.register_callback(_cb)
        executor = CodeExecutorAdapter()

        try:
            project = self._client.get_project(project_id)
            docs = self._client.get_knowledge_docs(project_id)
            knowledge_block = ""
            for doc in docs:
                filename = doc.get("filename", "doc")
                content = doc.get("content", "")
                knowledge_block += (
                    f"----- {filename} BEGIN -----\n{content}\n----- {filename} END -----\n\n"
                )

            first_message = (knowledge_block + requirement).strip()

            architect = ArchitectAgent(self._client, self._config, project_id, conv_name)
            reply = architect.send(first_message)
            reporter.emit_line_count("ArchitectAgent", reply)

            while not architect.is_complete(reply):
                reply = architect.send(GO_ON_PROMPT)
                reporter.emit_line_count("ArchitectAgent", reply)

            file_count = architect.extract_file_count(reply)
            task_doc = architect.get_task_document()

            router = TaskRouter(self._config.max_files_per_run)
            route = router.route(file_count)

            if route == "programmer":
                loop = ProgrammerLoop(self._client, self._config, executor, reporter)
                result = loop.run(task_doc, project)
                final = FinalResult(
                    task_id=task_id,
                    success=result.success,
                    root_dir=result.root_dir,
                    project_name=project.get("name", ""),
                    sub_results=[],
                    error_node=result.error_node,
                    error_reason=result.error_reason,
                )
            else:
                eng_loop = EngineerLoop(self._client, self._config, executor, reporter)
                sub_results = eng_loop.run(task_doc, project)
                success = all(r.success for r in sub_results)
                failed = next((r for r in sub_results if not r.success), None)
                root_dir = project.get("ai_work_dir", ".")
                final = FinalResult(
                    task_id=task_id,
                    success=success,
                    root_dir=root_dir,
                    project_name=project.get("name", ""),
                    sub_results=sub_results,
                    error_node=failed.error_node if failed else None,
                    error_reason=failed.error_reason if failed else None,
                )

            status.result = final
            status.state = "done" if final.success else "error"

        except Exception as e:
            status.state = "error"
            status.message = str(e)
            reporter.emit("error", "OnboardServer", f"Task failed: {e}")

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

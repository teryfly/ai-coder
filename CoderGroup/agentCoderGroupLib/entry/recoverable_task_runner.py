from __future__ import annotations

import threading
import traceback
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from ..adapters.chat_backend_client import ChatBackendClient, ChatBackendError
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..config.app_config import AppConfig
from ..orchestrator.architect_loop import ArchitectLoop
from ..orchestrator.engineer_loop import EngineerLoop
from ..orchestrator.programmer_loop import ProgrammerLoop
from ..orchestrator.task_router import TaskRouter
from ..recovery import ResumeCoordinator, TaskCheckpointStore, TaskEventLog, TaskStateMachine
from ..reporting.progress_reporter import ProgressReporter
from ..reporting.result_models import ProgressEvent

ProgressCallback = Callable[[ProgressEvent], None]
CompletionCallback = Callable[[str, bool, dict], None]


class RecoverableTaskRunner:
    def __init__(
        self,
        client: ChatBackendClient,
        config: AppConfig,
        executor: CodeExecutorAdapter,
        store: TaskCheckpointStore,
        coordinator: ResumeCoordinator,
        event_log: TaskEventLog,
    ):
        self._client = client
        self._config = config
        self._executor = executor
        self._store = store
        self._coordinator = coordinator
        self._event_log = event_log
        self._reply_events: dict[str, threading.Event] = {}
        self._reply_values: dict[str, str] = {}
        self._reply_lock = threading.Lock()
        self._completion_callbacks: dict[str, CompletionCallback] = {}

    def _pre_register_task_id(self, task_id: str) -> None:
        with self._reply_lock:
            self._reply_events.setdefault(task_id, threading.Event())

    def register_completion_callback(self, task_id: str, callback: CompletionCallback) -> None:
        """Register a callback to be invoked when task completes."""
        with self._reply_lock:
            self._completion_callbacks[task_id] = callback

    def start_task(
        self,
        project_id: int,
        requirement: str,
        conv_name: str,
        task_type: str,
        source: str,
        project_document_ids: Optional[list[int]] = None,
        conversation_document_ids: Optional[list[int]] = None,
        progress_callback: Optional[ProgressCallback] = None,
        predefined_task_id: str | None = None,
        completion_callback: Optional[CompletionCallback] = None,
    ) -> str:
        task_id = predefined_task_id or str(uuid.uuid4())
        snap = self._coordinator.create_snapshot(
            task_id=task_id,
            source=source,
            project_id=project_id,
            project=None,
            conv_name=conv_name,
            task_type=task_type,
            requirement=requirement,
            project_document_ids=project_document_ids or [],
            conversation_document_ids=conversation_document_ids or [],
        )
        self._store.save(snap)
        
        if completion_callback:
            self.register_completion_callback(task_id, completion_callback)
        
        t = threading.Thread(
            target=self._run_task_thread_safe,
            args=(task_id, None, progress_callback),
            daemon=True,
        )
        t.start()
        return task_id

    def resume_task(
        self, 
        task_id: str, 
        progress_callback: Optional[ProgressCallback] = None,
        completion_callback: Optional[CompletionCallback] = None,
    ) -> str:
        snap = self._store.load(task_id)
        if snap is None:
            raise KeyError(f"Task {task_id} not found")
        snap = TaskStateMachine.transition(snap, "running")
        self._store.save(snap)
        ctx = self._coordinator.build_resume_context(snap)
        
        if completion_callback:
            self.register_completion_callback(task_id, completion_callback)
        
        t = threading.Thread(
            target=self._run_task_thread_safe,
            args=(task_id, ctx, progress_callback),
            daemon=True,
        )
        t.start()
        return task_id

    def list_unfinished_tasks(self, source: str | None = None) -> list[dict]:
        return [x.to_dict() for x in self._coordinator.list_unfinished(source)]

    def send_user_reply(self, task_id: str, message: str) -> None:
        with self._reply_lock:
            self._reply_values[task_id] = message
            event = self._reply_events.get(task_id)
            if event is None:
                event = threading.Event()
                self._reply_events[task_id] = event
            event.set()

    def _emit(self, task_id: str, cb: Optional[ProgressCallback], event_type: str, agent: str, message: str) -> None:
        event = ProgressEvent(
            event_type=event_type,
            agent=agent,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        try:
            self._event_log.append_progress_event(task_id, event)
        except Exception:
            pass
        if cb:
            try:
                cb(event)
            except Exception:
                pass

    def _invoke_completion_callback(self, task_id: str, success: bool, summary: dict) -> None:
        """Invoke registered completion callback if exists."""
        with self._reply_lock:
            callback = self._completion_callbacks.pop(task_id, None)
        
        if callback:
            try:
                callback(task_id, success, summary)
            except Exception:
                pass

    def _bind_reporter(self, task_id: str, cb: Optional[ProgressCallback]) -> ProgressReporter:
        reporter = ProgressReporter(mode="callback")

        def safe_log(e):
            try:
                self._event_log.append_progress_event(task_id, e)
            except Exception:
                pass

        reporter.register_callback(safe_log)
        if cb:

            def safe_cb(e):
                try:
                    cb(e)
                except Exception:
                    pass

            reporter.register_callback(safe_cb)
        return reporter

    def _update_snapshot(self, task_id: str, **kwargs):
        snap = self._store.load(task_id)
        if snap is None:
            raise KeyError(f"Task {task_id} not found")
        for k, v in kwargs.items():
            setattr(snap, k, v)
        snap.updated_at = datetime.now(timezone.utc).isoformat()
        self._store.save(snap)
        return snap

    def _wait_for_user_reply(self, task_id: str) -> str:
        with self._reply_lock:
            event = self._reply_events.get(task_id)
            if event is None:
                event = threading.Event()
                self._reply_events[task_id] = event
        event.wait()
        with self._reply_lock:
            message = self._reply_values.pop(task_id, "continue")
            event.clear()
        return message

    def _make_user_reply_provider(self, task_id: str, cb: Optional[ProgressCallback]):
        def user_reply_provider(agent_name: str, latest_reply: str) -> str:
            self._update_snapshot(
                task_id,
                state="waiting_input",
                pending_user_input={"agent_name": agent_name, "latest_reply": latest_reply},
            )
            self._emit(task_id, cb, "user_input_required", agent_name, latest_reply)
            reply = self._wait_for_user_reply(task_id)
            self._update_snapshot(task_id, state="running", pending_user_input=None)
            return reply or "continue"

        return user_reply_provider

    def _run_task_thread_safe(self, task_id: str, resume_context, cb: Optional[ProgressCallback]) -> None:
        try:
            self._run_task_thread(task_id, resume_context, cb)
        except ChatBackendError as exc:
            error_msg = f"ChatBackendError: {exc}"
            try:
                self._update_snapshot(
                    task_id,
                    state="error",
                    error_reason=error_msg,
                    error_node="ChatBackendClient",
                )
                self._emit(task_id, cb, "error", "RecoverableTaskRunner", error_msg)
                self._invoke_completion_callback(task_id, False, {"error": error_msg})
            except Exception:
                pass
        except Exception as exc:
            error_msg = f"Unexpected error: {exc}"
            stack_trace = traceback.format_exc()
            try:
                self._update_snapshot(
                    task_id,
                    state="error",
                    error_reason=error_msg,
                    error_node=stack_trace,
                )
                self._emit(task_id, cb, "error", "RecoverableTaskRunner", error_msg)
                self._invoke_completion_callback(task_id, False, {"error": error_msg, "stack_trace": stack_trace})
            except Exception:
                pass

    def _run_task_thread(self, task_id: str, resume_context, cb: Optional[ProgressCallback]) -> None:
        snap = self._store.load(task_id)
        if snap is None:
            raise KeyError(f"Task {task_id} not found")
        project = snap.project or self._client.get_project(snap.project_id)
        snap = self._update_snapshot(task_id, project=project)
        if snap.project_document_ids:
            self._client.set_project_document_references(snap.project_id, snap.project_document_ids)

        reporter = self._bind_reporter(task_id, cb)
        provider = self._make_user_reply_provider(task_id, cb)

        stage = resume_context.current_stage if resume_context else ""
        if resume_context:
            if stage == "architect":
                self._run_new_dev(task_id, snap, project, reporter, provider, resume_context)
            elif stage == "engineer":
                task_doc = (snap.architect_result or {}).get("task_doc", snap.requirement)
                self._run_engineer(task_id, snap, project, task_doc, reporter, provider, resume_context)
            else:
                task_doc = (snap.architect_result or {}).get("task_doc", snap.requirement)
                self._run_programmer(task_id, snap, project, task_doc, reporter, provider, resume_context)
        elif snap.task_type == "formal_dev":
            self._run_engineer(task_id, snap, project, snap.requirement, reporter, provider, None)
        elif snap.task_type == "code_change":
            self._run_programmer(task_id, snap, project, snap.requirement, reporter, provider, None)
        else:
            self._run_new_dev(task_id, snap, project, reporter, provider, None)

        self._update_snapshot(task_id, state="done", current_stage="done")
        self._emit(task_id, cb, "complete", "RecoverableTaskRunner", "Task finished successfully")
        
        # Build completion summary
        final_snap = self._store.load(task_id)
        summary = {
            "project_name": final_snap.project.get("name", "") if final_snap and final_snap.project else "",
            "root_dir": final_snap.project.get("ai_work_dir", ".") if final_snap and final_snap.project else ".",
            "phases_completed": len(final_snap.engineer_completed_phases) if final_snap else 0,
            "conversations": dict(final_snap.conversation_names) if final_snap and final_snap.conversation_names else {},
        }
        
        self._invoke_completion_callback(task_id, True, summary)

    def _run_new_dev(self, task_id, snap, project, reporter, provider, ctx):
        docs = self._client.get_knowledge_docs(snap.project_id)
        kb = "".join(
            f"----- {d.get('filename', 'doc')} BEGIN -----\n{d.get('content', '')}\n"
            f"----- {d.get('filename', 'doc')} END -----\n\n"
            for d in docs
        )
        first_message = (kb + snap.requirement).strip()
        arch = ArchitectLoop(self._client, self._config, reporter).run(
            project_id=snap.project_id,
            conv_name=snap.conv_name,
            first_message=first_message,
            user_reply_provider=provider,
            conversation_document_ids=snap.conversation_document_ids,
            store=self._store,
            task_id=task_id,
            snapshot=snap,
            resume_context=ctx,
        )
        route = TaskRouter(self._config.max_files_per_run).route(arch.file_count)
        latest = self._store.load(task_id) or snap
        if route == "programmer":
            self._run_programmer(task_id, latest, project, arch.task_doc, reporter, provider, ctx)
        else:
            self._run_engineer(task_id, latest, project, arch.task_doc, reporter, provider, ctx)

    def _run_engineer(self, task_id, snap, project, task_doc, reporter, provider, ctx):
        self._update_snapshot(task_id, current_stage="engineer")
        use_stream = snap.source == "console"
        EngineerLoop(self._client, self._config, self._executor, reporter).run(
            task_doc=task_doc,
            project=project,
            user_reply_provider=provider,
            conversation_document_ids=snap.conversation_document_ids,
            conv_name=snap.conv_name,
            store=self._store,
            task_id=task_id,
            snapshot=snap,
            resume_context=ctx,
            use_stream=use_stream,
        )

    def _run_programmer(self, task_id, snap, project, task_doc, reporter, provider, ctx):
        self._update_snapshot(task_id, current_stage="programmer")
        use_stream = snap.source == "console"
        ProgrammerLoop(self._client, self._config, self._executor, reporter).run(
            task_doc=task_doc,
            project=project,
            user_reply_provider=provider,
            conversation_document_ids=snap.conversation_document_ids,
            conv_name=snap.conv_name,
            store=self._store,
            task_id=task_id,
            snapshot=snap,
            resume_context=ctx,
            use_stream=use_stream,
        )
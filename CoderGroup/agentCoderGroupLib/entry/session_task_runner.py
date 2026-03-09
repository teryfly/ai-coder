from __future__ import annotations

from ..adapters.chat_backend_client import ChatBackendClient
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..config.app_config import AppConfig
from ..config.task_types import TaskType
from ..recovery import ResumeCoordinator, TaskCheckpointStore, TaskEventLog
from ..reporting.result_models import FinalResult
from .console_ui import ConsoleUI
from .recoverable_task_runner import RecoverableTaskRunner


class SessionTaskRunner:
    def __init__(
        self,
        client: ChatBackendClient,
        config: AppConfig,
        executor: CodeExecutorAdapter,
        ui: ConsoleUI,
    ):
        self._client = client
        self._config = config
        self._executor = executor
        self._ui = ui
        self._store = TaskCheckpointStore(log_dir="log")
        self._event_log = TaskEventLog(log_dir="log")
        self._coordinator = ResumeCoordinator(self._store)
        self._runner = RecoverableTaskRunner(
            client=self._client,
            config=self._config,
            executor=self._executor,
            store=self._store,
            coordinator=self._coordinator,
            event_log=self._event_log,
        )

    def run(
        self,
        project: dict,
        conv_name: str,
        task_type: TaskType,
        requirement: str,
        conversation_document_ids: list[int] | None = None,
        existing_conversation_id: str | None = None,
    ) -> FinalResult:
        import time

        def progress_callback(event):
            self._ui.append_output(f"[{event.agent}] {event.message}")

        task_id = self._runner.start_task(
            project_id=int(project["id"]),
            requirement=requirement,
            conv_name=conv_name,
            task_type=task_type,
            source="console",
            project_document_ids=[],
            conversation_document_ids=conversation_document_ids or [],
            progress_callback=progress_callback,
        )

        self._ui.append_output(f"Task {task_id} started. Monitoring progress...")

        while True:
            snap = self._store.load(task_id)
            if snap is None:
                error_msg = f"Task {task_id} snapshot not found"
                self._ui.append_output(f"=== Error: {error_msg} ===")
                return FinalResult(
                    task_id=task_id,
                    success=False,
                    root_dir=project.get("ai_work_dir", "."),
                    project_name=project.get("name", ""),
                    sub_results=[],
                    error_reason=error_msg,
                )

            if snap.state == "done":
                self._ui.append_output("=== Task Completed Successfully ===")
                self._print_task_summary(snap)
                return FinalResult(
                    task_id=task_id,
                    success=True,
                    root_dir=snap.project.get("ai_work_dir", ".") if snap.project else ".",
                    project_name=snap.project.get("name", "") if snap.project else "",
                    sub_results=[],
                )

            if snap.state == "error":
                self._ui.append_output(f"=== Task Failed: {snap.error_reason} ===")
                self._print_task_summary(snap)
                return FinalResult(
                    task_id=task_id,
                    success=False,
                    root_dir=snap.project.get("ai_work_dir", ".") if snap.project else ".",
                    project_name=snap.project.get("name", "") if snap.project else "",
                    sub_results=[],
                    error_node=snap.error_node,
                    error_reason=snap.error_reason,
                )

            if snap.state == "waiting_input" and snap.pending_user_input:
                agent_name = str(snap.pending_user_input.get("agent_name", "agent"))
                latest_reply = str(snap.pending_user_input.get("latest_reply", ""))
                self._ui.append_output(f"[{agent_name}] {latest_reply}")
                reply = self._ui.prompt_input(f"{agent_name}> ")
                if ConsoleUI.is_exit_command(reply):
                    self._ui.append_output("Task interrupted by user. State saved for later resume.")
                    return FinalResult(
                        task_id=task_id,
                        success=False,
                        root_dir=snap.project.get("ai_work_dir", ".") if snap.project else ".",
                        project_name=snap.project.get("name", "") if snap.project else "",
                        sub_results=[],
                        error_reason="User interrupted",
                    )
                self._runner.send_user_reply(task_id, reply)

            time.sleep(2)

    def _print_task_summary(self, snap) -> None:
        self._ui.append_output("")
        self._ui.append_output("=== Task Execution Summary ===")
        self._ui.append_output(f"Task ID: {snap.task_id}")
        self._ui.append_output(f"Task Type: {snap.task_type}")
        self._ui.append_output(f"Project: {snap.project.get('name', 'N/A') if snap.project else 'N/A'}")
        self._ui.append_output(f"Final State: {snap.state}")
        self._ui.append_output(f"Root Directory: {snap.project.get('ai_work_dir', 'N/A') if snap.project else 'N/A'}")
        self._ui.append_output("")

        if snap.conversation_names:
            self._ui.append_output("Conversations Used:")
            for role, name in snap.conversation_names.items():
                conv_id = snap.conversation_ids.get(role, "N/A")
                self._ui.append_output(f"  - {role.capitalize()}: {name} (ID: {conv_id})")
            self._ui.append_output("")

        if snap.engineer_completed_phases:
            self._ui.append_output(f"Engineer Phases Completed: {len(snap.engineer_completed_phases)}")
            for phase_id in snap.engineer_completed_phases:
                phase_conv = snap.programmer_phase_conversations.get(phase_id, "N/A")
                phase_name = snap.programmer_phase_names.get(phase_id, "N/A")
                self._ui.append_output(f"  - Phase {phase_id}: {phase_name} (Conv ID: {phase_conv})")
            self._ui.append_output("")

        if snap.programmer_step_progress:
            x, y = snap.programmer_step_progress if len(snap.programmer_step_progress) >= 2 else (0, 0)
            self._ui.append_output(f"Programmer Steps: {x}/{y}")
            self._ui.append_output("")

        if snap.error_reason:
            self._ui.append_output(f"Error: {snap.error_reason}")
            if snap.error_node:
                self._ui.append_output(f"Error Node: {snap.error_node}")

        self._ui.append_output("=" * 50)
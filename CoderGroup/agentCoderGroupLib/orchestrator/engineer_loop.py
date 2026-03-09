from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Optional

from ..adapters.chat_backend_client import ChatBackendClient
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..agents.engineer_agent import EngineerAgent
from ..config.app_config import AppConfig
from ..config.constants import CONTINUE_PROMPT, ENGINEER_TERM_RE
from ..reporting.progress_reporter import ProgressReporter
from ..reporting.result_models import SubTaskResult

if TYPE_CHECKING:
    from ..recovery.checkpoint_store import TaskCheckpointStore
    from ..recovery.task_snapshot import ResumeContext, TaskSnapshot

UserReplyProvider = Callable[[str, str], str]


def _engineer_has_more_phases(reply: str) -> bool:
    return bool(ENGINEER_TERM_RE.search(reply or ""))


class EngineerLoop:
    def __init__(
        self,
        client: ChatBackendClient,
        config: AppConfig,
        executor: CodeExecutorAdapter,
        reporter: ProgressReporter,
    ):
        self._client = client
        self._config = config
        self._executor = executor
        self._reporter = reporter

    def _request_user_reply(self, provider: Optional[UserReplyProvider], latest_reply: str) -> str:
        self._reporter.emit(
            "user_input_required",
            "EngineerAgent",
            "Engineer reply requires user/CIO input before continuing.",
        )
        if provider is None:
            raise RuntimeError("Engineer requires input but no user_reply_provider is available.")
        return provider("EngineerAgent", latest_reply).strip() or "continue"

    def run(
        self,
        task_doc: str,
        project: dict,
        user_reply_provider: Optional[UserReplyProvider] = None,
        conversation_document_ids: Optional[list[int]] = None,
        conv_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        store: "TaskCheckpointStore | None" = None,
        task_id: str | None = None,
        snapshot: "TaskSnapshot | None" = None,
        resume_context: "ResumeContext | None" = None,
    ) -> list[SubTaskResult]:
        from .programmer_loop import ProgrammerLoop
        from .task_router import TaskRouter

        project_id = int(project.get("id", 0) or 0)
        base_conv_name = conv_name or f"engineer-{project.get('name', 'task')}"
        conv_id_to_use = conversation_id or (resume_context.engineer_conv_id if resume_context else None)

        agent = EngineerAgent(
            self._client,
            self._config,
            project_id,
            base_conv_name,
            conversation_document_ids=conversation_document_ids,
            conversation_id=conv_id_to_use,
        )
        router = TaskRouter(self._config.max_files_per_run)

        if store and task_id and snapshot:
            snapshot.engineer_conv_id = agent.conversation_id
            if not isinstance(snapshot.conversation_ids, dict):
                snapshot.conversation_ids = {}
            snapshot.conversation_ids["engineer"] = agent.conversation_id
            snapshot.updated_at = datetime.now(timezone.utc).isoformat()
            store.save(snapshot)

        self._reporter.emit("status", "EngineerAgent", "Starting engineer loop...")
        reply = agent.send(task_doc)
        self._reporter.emit_line_count("EngineerAgent", reply)

        results: list[SubTaskResult] = []
        completed = set(resume_context.engineer_completed_phases if resume_context else [])

        while True:
            if not agent.is_complete(reply):
                reply = agent.send(self._request_user_reply(user_reply_provider, reply))
                self._reporter.emit_line_count("EngineerAgent", reply)
                continue

            phase_id = agent.extract_phase_id(reply)
            file_count = agent.extract_file_count(reply)
            sub_phase_doc = agent.extract_sub_phase_doc(reply)

            if phase_id in completed:
                reply = agent.send(CONTINUE_PROMPT)
                self._reporter.emit_line_count("EngineerAgent", reply)
                if not _engineer_has_more_phases(reply):
                    break
                continue

            if store and task_id and snapshot:
                snapshot.engineer_current_phase = phase_id
                snapshot.current_stage = "engineer"
                snapshot.updated_at = datetime.now(timezone.utc).isoformat()
                store.save(snapshot)

            self._reporter.emit(
                "status",
                "EngineerAgent",
                f"Processing phase {phase_id} ({file_count} estimated files)",
            )

            route = router.route(file_count)
            if route == "programmer":
                pr = ProgrammerLoop(self._client, self._config, self._executor, self._reporter).run(
                    sub_phase_doc,
                    project,
                    user_reply_provider=user_reply_provider,
                    conversation_document_ids=conversation_document_ids,
                    conv_name=f"{base_conv_name}-phase-{phase_id}",
                    conversation_id=None,
                    store=store,
                    task_id=task_id,
                    snapshot=snapshot,
                    resume_context=None,
                )
                sub_result = SubTaskResult(
                    phase_id=phase_id,
                    success=pr.success,
                    programmer_results=[pr],
                    error_node=pr.error_node,
                    error_reason=pr.error_reason,
                )
            else:
                nested = self.run(
                    sub_phase_doc,
                    project,
                    user_reply_provider=user_reply_provider,
                    conversation_document_ids=conversation_document_ids,
                    conv_name=f"{base_conv_name}-phase-{phase_id}",
                    conversation_id=None,
                    store=store,
                    task_id=task_id,
                    snapshot=snapshot,
                    resume_context=None,
                )
                success = all(r.success for r in nested)
                failed = next((r for r in nested if not r.success), None)
                sub_result = SubTaskResult(
                    phase_id=phase_id,
                    success=success,
                    programmer_results=[pr for r in nested for pr in r.programmer_results],
                    error_node=failed.error_node if failed else None,
                    error_reason=failed.error_reason if failed else None,
                )

            results.append(sub_result)
            completed.add(phase_id)

            if store and task_id and snapshot:
                if phase_id not in snapshot.engineer_completed_phases:
                    snapshot.engineer_completed_phases.append(phase_id)
                snapshot.engineer_current_phase = phase_id
                snapshot.current_stage = "engineer"
                snapshot.updated_at = datetime.now(timezone.utc).isoformat()
                store.save(snapshot)

            reply = agent.send(CONTINUE_PROMPT)
            self._reporter.emit_line_count("EngineerAgent", reply)
            if not _engineer_has_more_phases(reply):
                break

        return results
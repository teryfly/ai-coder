from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Optional

from ..adapters.chat_backend_client import ChatBackendClient
from ..agents.architect_agent import ArchitectAgent
from ..config.app_config import AppConfig
from ..reporting.progress_reporter import ProgressReporter

if TYPE_CHECKING:
    from ..recovery.checkpoint_store import TaskCheckpointStore
    from ..recovery.task_snapshot import ResumeContext, TaskSnapshot

UserReplyProvider = Callable[[str, str], str]


@dataclass
class ArchitectLoopResult:
    conversation_id: str
    task_doc: str
    file_count: int


class ArchitectLoop:
    def __init__(self, client: ChatBackendClient, config: AppConfig, reporter: ProgressReporter):
        self._client = client
        self._config = config
        self._reporter = reporter

    def run(
        self,
        project_id: int,
        conv_name: str,
        first_message: str,
        user_reply_provider: UserReplyProvider,
        conversation_document_ids: Optional[list[int]] = None,
        conversation_id: Optional[str] = None,
        store: "TaskCheckpointStore | None" = None,
        task_id: str | None = None,
        snapshot: "TaskSnapshot | None" = None,
        resume_context: "ResumeContext | None" = None,
    ) -> ArchitectLoopResult:
        if resume_context and resume_context.architect_done and resume_context.architect_result:
            result = resume_context.architect_result
            return ArchitectLoopResult(
                conversation_id=resume_context.architect_conv_id or "",
                task_doc=str(result.get("task_doc", "")),
                file_count=int(result.get("file_count", 0) or 0),
            )

        conv_id_to_use = conversation_id
        if not conv_id_to_use and resume_context and resume_context.architect_conv_id:
            conv_id_to_use = resume_context.architect_conv_id

        agent = ArchitectAgent(
            self._client,
            self._config,
            project_id,
            conv_name,
            conversation_document_ids=conversation_document_ids,
            conversation_id=conv_id_to_use,
        )

        self._reporter.emit("status", "ArchitectAgent", "Starting architect phase...")
        reply = agent.send(first_message)
        self._reporter.emit_line_count("ArchitectAgent", reply)

        while not agent.is_complete(reply):
            self._reporter.emit(
                "user_input_required",
                "ArchitectAgent",
                "Architect reply requires user/CIO input before continuing.",
            )
            user_message = user_reply_provider("ArchitectAgent", reply).strip() or "continue"
            reply = agent.send(user_message)
            self._reporter.emit_line_count("ArchitectAgent", reply)

        file_count = agent.extract_file_count(reply)
        task_doc = agent.get_task_document()

        if store and task_id and snapshot:
            if not isinstance(snapshot.conversation_ids, dict):
                snapshot.conversation_ids = {}
            snapshot.conversation_ids["architect"] = agent.conversation_id
            snapshot.architect_result = {"task_doc": task_doc, "file_count": file_count}
            snapshot.current_stage = "engineer"
            snapshot.updated_at = datetime.now(timezone.utc).isoformat()
            store.save(snapshot)

        self._reporter.emit("status", "ArchitectAgent", f"Architect complete. Estimated files: {file_count}")
        return ArchitectLoopResult(
            conversation_id=agent.conversation_id,
            task_doc=task_doc,
            file_count=file_count,
        )
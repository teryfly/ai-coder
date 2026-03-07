from dataclasses import dataclass
from typing import Callable, Optional

from ..adapters.chat_backend_client import ChatBackendClient
from ..agents.architect_agent import ArchitectAgent
from ..config.app_config import AppConfig
from ..reporting.progress_reporter import ProgressReporter

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
    ) -> ArchitectLoopResult:
        agent = ArchitectAgent(
            self._client,
            self._config,
            project_id,
            conv_name,
            conversation_document_ids=conversation_document_ids,
            conversation_id=conversation_id,
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

        self._reporter.emit("status", "ArchitectAgent", f"Architect complete. Estimated files: {file_count}")
        return ArchitectLoopResult(
            conversation_id=agent.conversation_id,
            task_doc=task_doc,
            file_count=file_count,
        )
from ..adapters.chat_backend_client import ChatBackendClient
from ..config.app_config import AppConfig
from ..orchestrator.reply_rules import architect_is_complete, extract_architect_file_count
from .base_agent import BaseAgent


class ArchitectAgent(BaseAgent):
    def __init__(
        self,
        client: ChatBackendClient,
        config: AppConfig,
        project_id: int,
        conv_name: str,
        conversation_document_ids: list[int] | None = None,
        conversation_id: str | None = None,
    ):
        super().__init__(
            client,
            config,
            project_id,
            conv_name,
            "architect",
            conversation_document_ids=conversation_document_ids,
            conversation_id=conversation_id,
        )

    def is_complete(self, reply: str) -> bool:
        return architect_is_complete(reply)

    def extract_file_count(self, reply: str) -> int:
        return extract_architect_file_count(reply)

    def get_task_document(self) -> str:
        return self.get_last_reply()
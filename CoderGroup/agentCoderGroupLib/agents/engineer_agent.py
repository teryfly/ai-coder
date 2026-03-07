from ..adapters.chat_backend_client import ChatBackendClient
from ..config.app_config import AppConfig
from ..orchestrator.reply_rules import engineer_is_complete, extract_engineer_phase_and_file_count
from .base_agent import BaseAgent


class EngineerAgent(BaseAgent):
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
            "engineer",
            conversation_document_ids=conversation_document_ids,
            conversation_id=conversation_id,
        )

    def is_complete(self, reply: str) -> bool:
        return engineer_is_complete(reply)

    def extract_sub_phase_doc(self, reply: str) -> str:
        return reply

    def extract_file_count(self, reply: str) -> int:
        _phase_id, file_count = extract_engineer_phase_and_file_count(reply)
        return file_count

    def extract_phase_id(self, reply: str) -> str:
        phase_id, _file_count = extract_engineer_phase_and_file_count(reply)
        return phase_id
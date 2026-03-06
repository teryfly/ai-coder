from ..adapters.chat_backend_client import ChatBackendClient
from ..config.app_config import AppConfig
from ..config.constants import ENGINEER_TERM_RE
from .base_agent import BaseAgent


class EngineerAgent(BaseAgent):
    def __init__(
        self, client: ChatBackendClient, config: AppConfig, project_id: int, conv_name: str
    ):
        super().__init__(client, config, project_id, conv_name, "engineer")

    def is_complete(self, reply: str) -> bool:
        return bool(ENGINEER_TERM_RE.search(reply))

    def extract_sub_phase_doc(self, reply: str) -> str:
        return reply

    def extract_file_count(self, reply: str) -> int:
        m = ENGINEER_TERM_RE.search(reply)
        if not m:
            raise ValueError("Engineer termination line not found")
        return int(m.group(2))

    def extract_phase_id(self, reply: str) -> str:
        m = ENGINEER_TERM_RE.search(reply)
        if not m:
            raise ValueError("Engineer termination line not found")
        return m.group(1)

from ..adapters.chat_backend_client import ChatBackendClient
from ..config.app_config import AppConfig
from ..config.constants import ARCHITECT_TERM_RE
from .base_agent import BaseAgent


class ArchitectAgent(BaseAgent):
    def __init__(
        self, client: ChatBackendClient, config: AppConfig, project_id: int, conv_name: str
    ):
        super().__init__(client, config, project_id, conv_name, "architect")

    def is_complete(self, reply: str) -> bool:
        lines = [l.rstrip() for l in reply.splitlines() if l.strip()]
        if not lines:
            return False
        last_line = lines[-1].rstrip(".,;:!? \t")
        return bool(ARCHITECT_TERM_RE.search(last_line))

    def extract_file_count(self, reply: str) -> int:
        lines = [l.rstrip() for l in reply.splitlines() if l.strip()]
        if not lines:
            raise ValueError("Empty reply, termination line not found")
        last_line = lines[-1].rstrip(".,;:!? \t")
        m = ARCHITECT_TERM_RE.search(last_line)
        if not m:
            raise ValueError("Termination line not found")
        return int(m.group(1))

    def get_task_document(self) -> str:
        return self.get_last_reply()

from ..adapters.chat_backend_client import ChatBackendClient
from ..config.app_config import AppConfig
from ..config.constants import STEP_RE
from .base_agent import BaseAgent


class ProgrammerAgent(BaseAgent):
    def __init__(
        self, client: ChatBackendClient, config: AppConfig, project_id: int, conv_name: str
    ):
        super().__init__(client, config, project_id, conv_name, "programmer")
        self.accumulated_output: str = ""

    def send(self, message: str) -> str:
        reply = super().send(message)
        self.accumulated_output += reply + "\n"
        return reply

    def is_complete(self, reply: str) -> bool:
        x, y = self.extract_step_progress(reply)
        return x >= y

    def extract_step_progress(self, text: str) -> tuple[int, int]:
        matches = STEP_RE.findall(text)
        if not matches:
            return (0, 1)
        x, y = matches[-1]
        return (int(x), int(y))

    def get_full_code_output(self) -> str:
        return self.accumulated_output

    def format_error_feedback(self, step_desc: str, error: str) -> str:
        return (
            f"The following shell command in Step {step_desc} failed dry_run validation:\n"
            f"Error: {error}\n"
            f"Please revise the affected steps and continue from Step {step_desc}."
        )

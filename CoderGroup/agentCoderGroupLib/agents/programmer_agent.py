from ..adapters.chat_backend_client import ChatBackendClient
from ..config.app_config import AppConfig
from ..orchestrator.reply_rules import (
    extract_last_step_progress,
    programmer_is_complete,
    programmer_should_auto_continue,
)
from .base_agent import BaseAgent


class ProgrammerAgent(BaseAgent):
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
            "programmer",
            conversation_document_ids=conversation_document_ids,
            conversation_id=conversation_id,
        )
        self.accumulated_output: str = ""

    def send(self, message: str) -> str:
        reply = super().send(message)
        self.accumulated_output += reply + "\n"
        return reply

    def is_complete(self, reply: str) -> bool:
        return programmer_is_complete(reply)

    def should_auto_continue(self, text: str) -> bool:
        return programmer_should_auto_continue(text)

    def extract_step_progress(self, text: str) -> tuple[int, int]:
        progress = extract_last_step_progress(text)
        if progress is None:
            return (0, 1)
        return (progress.x, progress.y)

    def get_full_code_output(self) -> str:
        return self.accumulated_output

    def format_error_feedback(self, step_desc: str, error: str) -> str:
        return (
            f"The following shell command in Step {step_desc} failed dry_run validation:\n"
            f"Error: {error}\n"
            f"Please revise the affected steps and continue from Step {step_desc}."
        )
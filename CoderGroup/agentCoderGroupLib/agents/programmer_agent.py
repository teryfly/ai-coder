from typing import Callable, Generator

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
        inject_source_code: bool = False,
    ):
        self._inject_source_code = inject_source_code
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
        self.current_line_count: int = 0

    def _augment_system_prompt(self, base_prompt: str, project_id: int) -> str:
        if not self._inject_source_code:
            return base_prompt

        try:
            source_code = self._client.get_project_source_code(project_id)
            if not source_code or len(source_code.strip()) <= 1:
                return base_prompt

            augmented = base_prompt.rstrip() + "\n\n"
            augmented += "--- The File Structure and Source Code of this Project BEGIN---\n"
            augmented += source_code.strip() + "\n"
            augmented += "--- The File Structure and Source Code of this Project END---\n"
            return augmented
        except Exception:
            return base_prompt

    def send(self, message: str) -> str:
        reply = super().send(message)
        self.accumulated_output += reply + "\n"
        self.current_line_count = self.accumulated_output.count('\n') + 1
        return reply

    def send_stream(
        self, 
        message: str, 
        on_chunk: Callable[[str, int, bool], None] | None = None
    ) -> Generator[tuple[str, int, bool], None, str]:
        """
        Send message with streaming and update accumulated output.
        
        Args:
            message: Message to send
            on_chunk: Optional callback(chunk_text, total_line_count, is_final)
        
        Yields:
            tuple[chunk_text, total_line_count, is_final]
        
        Returns:
            Complete reply
        """
        reply_start_lines = self.accumulated_output.count('\n') + 1
        
        for chunk_text, _chunk_lines, is_final in super().send_stream(message, on_chunk=None):
            self.accumulated_output += chunk_text
            total_lines = self.accumulated_output.count('\n') + 1
            self.current_line_count = total_lines
            
            if on_chunk:
                on_chunk(chunk_text, total_lines, is_final)
            
            yield chunk_text, total_lines, is_final
        
        reply = self.get_last_reply()
        self.accumulated_output += "\n"
        
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

    def get_current_line_count(self) -> int:
        return self.current_line_count

    def format_error_feedback(self, step_desc: str, error: str) -> str:
        return (
            f"The following shell command in Step {step_desc} failed dry_run validation:\n"
            f"Error: {error}\n"
            f"Please revise the affected steps and continue from Step {step_desc}."
        )
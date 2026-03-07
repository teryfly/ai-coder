from typing import Callable, Optional

from ..adapters.chat_backend_client import ChatBackendClient
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..agents.programmer_agent import ProgrammerAgent
from ..config.app_config import AppConfig
from ..config.constants import GO_ON_PROMPT
from ..reporting.progress_reporter import ProgressReporter
from ..reporting.result_models import ExecutionResult, ProgrammerResult
from .execution_pipeline import ExecutionPipeline

UserReplyProvider = Callable[[str, str], str]


class ProgrammerLoop:
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

    def _request_user_reply(self, provider: Optional[UserReplyProvider], latest_reply: str) -> Optional[str]:
        self._reporter.emit(
            "user_input_required",
            "ProgrammerAgent",
            "Programmer reply requires user/CIO input before continuing.",
        )
        if provider is None:
            return None
        return provider("ProgrammerAgent", latest_reply).strip()

    def run(
        self,
        task_doc: str,
        project: dict,
        user_reply_provider: Optional[UserReplyProvider] = None,
        conversation_document_ids: Optional[list[int]] = None,
        conv_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> ProgrammerResult:
        root_dir = project.get("ai_work_dir", ".")
        project_id = int(project.get("id", 0) or 0)
        conversation_name = conv_name or f"programmer-{project.get('name', 'task')}"

        agent = ProgrammerAgent(
            self._client,
            self._config,
            project_id,
            conversation_name,
            conversation_document_ids=conversation_document_ids,
            conversation_id=conversation_id,
        )
        self._reporter.emit("status", "ProgrammerAgent", "Starting programmer loop...")

        reply = agent.send(task_doc)
        self._reporter.emit_line_count("ProgrammerAgent", reply)

        while not agent.is_complete(agent.get_full_code_output()):
            if agent.should_auto_continue(agent.get_full_code_output()):
                reply = agent.send(GO_ON_PROMPT)
                self._reporter.emit_line_count("ProgrammerAgent", reply)
                continue

            user_message = self._request_user_reply(user_reply_provider, reply)
            if user_message is None:
                err = "Programmer requires input but no user_reply_provider is available."
                return ProgrammerResult(
                    success=False,
                    steps_completed=0,
                    root_dir=root_dir,
                    execution_result=ExecutionResult(success=False, summary={}, error=err),
                    error_node=agent.conversation_id,
                    error_reason=err,
                )

            reply = agent.send(user_message or "continue")
            self._reporter.emit_line_count("ProgrammerAgent", reply)

        full_output = agent.get_full_code_output()
        x, _y = agent.extract_step_progress(full_output)

        pipeline = ExecutionPipeline(self._executor, self._reporter)
        exec_result = pipeline.run(full_output, root_dir, agent)

        if not exec_result.success:
            return ProgrammerResult(
                success=False,
                steps_completed=x,
                root_dir=root_dir,
                execution_result=exec_result,
                error_node=agent.conversation_id,
                error_reason=exec_result.error,
            )

        return ProgrammerResult(
            success=True,
            steps_completed=x,
            root_dir=root_dir,
            execution_result=exec_result,
        )
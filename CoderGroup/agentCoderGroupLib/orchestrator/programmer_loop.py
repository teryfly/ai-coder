from ..adapters.chat_backend_client import ChatBackendClient
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..agents.programmer_agent import ProgrammerAgent
from ..config.app_config import AppConfig
from ..config.constants import GO_ON_PROMPT
from ..reporting.progress_reporter import ProgressReporter
from ..reporting.result_models import ProgrammerResult
from .execution_pipeline import ExecutionPipeline


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

    def run(self, task_doc: str, project: dict) -> ProgrammerResult:
        root_dir = project.get("ai_work_dir", ".")
        project_id = project.get("id", 0)
        conv_name = f"programmer-{project.get('name', 'task')}"

        agent = ProgrammerAgent(self._client, self._config, project_id, conv_name)

        self._reporter.emit("status", "ProgrammerAgent", "Starting programmer loop...")

        reply = agent.send(task_doc)
        self._reporter.emit_line_count("ProgrammerAgent", reply)

        while not agent.is_complete(reply):
            reply = agent.send(GO_ON_PROMPT)
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

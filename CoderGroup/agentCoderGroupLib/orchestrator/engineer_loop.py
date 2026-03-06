from ..adapters.chat_backend_client import ChatBackendClient
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..agents.engineer_agent import EngineerAgent
from ..config.app_config import AppConfig
from ..config.constants import CONTINUE_PROMPT
from ..reporting.progress_reporter import ProgressReporter
from ..reporting.result_models import SubTaskResult


class EngineerLoop:
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

    def run(self, task_doc: str, project: dict) -> list[SubTaskResult]:
        # Lazy imports to avoid circular dependency
        from .programmer_loop import ProgrammerLoop
        from .task_router import TaskRouter

        project_id = project.get("id", 0)
        conv_name = f"engineer-{project.get('name', 'task')}"

        agent = EngineerAgent(self._client, self._config, project_id, conv_name)
        router = TaskRouter(self._config.max_files_per_run)

        self._reporter.emit("status", "EngineerAgent", "Starting engineer loop...")

        reply = agent.send(task_doc)
        self._reporter.emit_line_count("EngineerAgent", reply)

        results: list[SubTaskResult] = []

        while agent.is_complete(reply):
            phase_id = agent.extract_phase_id(reply)
            file_count = agent.extract_file_count(reply)
            sub_phase_doc = agent.extract_sub_phase_doc(reply)

            self._reporter.emit(
                "status",
                "EngineerAgent",
                f"Processing phase {phase_id} ({file_count} estimated files)",
            )

            route = router.route(file_count)
            if route == "programmer":
                prog_loop = ProgrammerLoop(
                    self._client, self._config, self._executor, self._reporter
                )
                prog_result = prog_loop.run(sub_phase_doc, project)
                sub_result = SubTaskResult(
                    phase_id=phase_id,
                    success=prog_result.success,
                    programmer_results=[prog_result],
                    error_node=prog_result.error_node,
                    error_reason=prog_result.error_reason,
                )
            else:
                nested = self.run(sub_phase_doc, project)
                success = all(r.success for r in nested)
                failed = next((r for r in nested if not r.success), None)
                sub_result = SubTaskResult(
                    phase_id=phase_id,
                    success=success,
                    programmer_results=[
                        pr for r in nested for pr in r.programmer_results
                    ],
                    error_node=failed.error_node if failed else None,
                    error_reason=failed.error_reason if failed else None,
                )

            results.append(sub_result)

            reply = agent.send(CONTINUE_PROMPT)
            self._reporter.emit_line_count("EngineerAgent", reply)

            if not agent.is_complete(reply):
                break

        return results

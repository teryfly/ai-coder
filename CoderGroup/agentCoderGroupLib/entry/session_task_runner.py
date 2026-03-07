from __future__ import annotations

from ..adapters.chat_backend_client import ChatBackendClient, ChatBackendError
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..config.app_config import AppConfig
from ..config.task_types import TaskType
from ..orchestrator.architect_loop import ArchitectLoop
from ..orchestrator.engineer_loop import EngineerLoop
from ..orchestrator.programmer_loop import ProgrammerLoop
from ..orchestrator.task_router import TaskRouter
from ..reporting.progress_reporter import ProgressReporter
from ..reporting.result_models import FinalResult
from .console_ui import ConsoleUI


class SessionTaskRunner:
    def __init__(
        self,
        client: ChatBackendClient,
        config: AppConfig,
        executor: CodeExecutorAdapter,
        ui: ConsoleUI,
    ):
        self._client = client
        self._config = config
        self._executor = executor
        self._ui = ui

    def run(
        self,
        project: dict,
        conv_name: str,
        task_type: TaskType,
        requirement: str,
        conversation_document_ids: list[int] | None = None,
        existing_conversation_id: str | None = None,
    ) -> FinalResult:
        reporter = ProgressReporter(mode="console")
        user_reply_provider = self._build_user_reply_provider()

        if task_type == "formal_dev":
            return self._run_formal_dev(
                project,
                conv_name,
                requirement,
                reporter,
                user_reply_provider,
                conversation_document_ids,
                existing_conversation_id,
            )
        if task_type == "code_change":
            return self._run_code_change(
                project,
                conv_name,
                requirement,
                reporter,
                user_reply_provider,
                conversation_document_ids,
                existing_conversation_id,
            )
        return self._run_new_dev(
            project,
            conv_name,
            requirement,
            reporter,
            user_reply_provider,
            conversation_document_ids,
            existing_conversation_id,
        )

    def _run_new_dev(self, project, conv_name, requirement, reporter, user_reply_provider, conv_docs, existing_id):
        docs = []
        try:
            docs = self._client.get_knowledge_docs(int(project["id"]))
        except ChatBackendError as exc:
            self._ui.append_output(f"[Warning] Failed to load knowledge docs: {exc}")

        knowledge_block = "".join(
            f"----- {d.get('filename', 'doc')} BEGIN -----\n{d.get('content', '')}\n----- {d.get('filename', 'doc')} END -----\n\n"
            for d in docs
        )
        first_message = (knowledge_block + requirement).strip()

        arch = ArchitectLoop(self._client, self._config, reporter).run(
            project_id=int(project["id"]),
            conv_name=conv_name,
            first_message=first_message,
            user_reply_provider=user_reply_provider,
            conversation_document_ids=conv_docs,
            conversation_id=existing_id,
        )
        route = TaskRouter(self._config.max_files_per_run).route(arch.file_count)
        self._ui.append_output(f"Routing decision: {route}")

        if route == "programmer":
            p = ProgrammerLoop(self._client, self._config, self._executor, reporter).run(
                arch.task_doc,
                project,
                user_reply_provider=user_reply_provider,
                conversation_document_ids=conv_docs,
            )
            return FinalResult(
                task_id=arch.conversation_id,
                success=p.success,
                root_dir=p.root_dir,
                project_name=project.get("name", ""),
                sub_results=[],
                error_node=p.error_node,
                error_reason=p.error_reason,
            )

        sub = EngineerLoop(self._client, self._config, self._executor, reporter).run(
            arch.task_doc,
            project,
            user_reply_provider=user_reply_provider,
            conversation_document_ids=conv_docs,
        )
        success = all(r.success for r in sub)
        failed = next((r for r in sub if not r.success), None)
        return FinalResult(
            task_id=arch.conversation_id,
            success=success,
            root_dir=project.get("ai_work_dir", "."),
            project_name=project.get("name", ""),
            sub_results=sub,
            error_node=failed.error_node if failed else None,
            error_reason=failed.error_reason if failed else None,
        )

    def _run_formal_dev(self, project, conv_name, requirement, reporter, user_reply_provider, conv_docs, existing_id):
        sub = EngineerLoop(self._client, self._config, self._executor, reporter).run(
            requirement,
            project,
            user_reply_provider=user_reply_provider,
            conversation_document_ids=conv_docs,
            conv_name=conv_name,
            conversation_id=existing_id,
        )
        success = all(r.success for r in sub)
        failed = next((r for r in sub if not r.success), None)
        return FinalResult(
            task_id=existing_id or conv_name,
            success=success,
            root_dir=project.get("ai_work_dir", "."),
            project_name=project.get("name", ""),
            sub_results=sub,
            error_node=failed.error_node if failed else None,
            error_reason=failed.error_reason if failed else None,
        )

    def _run_code_change(self, project, conv_name, requirement, reporter, user_reply_provider, conv_docs, existing_id):
        p = ProgrammerLoop(self._client, self._config, self._executor, reporter).run(
            requirement,
            project,
            user_reply_provider=user_reply_provider,
            conversation_document_ids=conv_docs,
            conv_name=conv_name,
            conversation_id=existing_id,
        )
        return FinalResult(
            task_id=existing_id or conv_name,
            success=p.success,
            root_dir=p.root_dir,
            project_name=project.get("name", ""),
            sub_results=[],
            error_node=p.error_node,
            error_reason=p.error_reason,
        )

    def _build_user_reply_provider(self):
        def user_reply_provider(agent_name: str, latest_reply: str) -> str:
            self._ui.append_output(f"[{agent_name}] needs your input.")
            self._ui.append_output(latest_reply)
            msg = self._ui.prompt_input(f"{agent_name}> ")
            if ConsoleUI.is_exit_command(msg):
                raise SystemExit(0)
            return msg

        return user_reply_provider
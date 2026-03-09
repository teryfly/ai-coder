from ..adapters.chat_backend_client import ChatBackendClient, ChatBackendError
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..config.app_config import AppConfig, load_config, load_prompt
from ..config.task_types import TaskType, get_agent_key_for_task_type
from ..recovery import ResumeCoordinator, TaskCheckpointStore, TaskEventLog
from ..reporting.result_models import FinalResult
from .console_ui import ConsoleUI
from .document_reference_selector import DocumentReferenceSelector
from .project_selector import ProjectSelector
from .recoverable_task_runner import RecoverableTaskRunner
from .session_task_runner import SessionTaskRunner
from .task_type_selector import TaskTypeSelector


class ConsoleRunner:
    def __init__(self, config: AppConfig):
        self._config = config
        self._client = ChatBackendClient(config.chat_backend_url, config.chat_backend_token)
        self._executor = CodeExecutorAdapter()
        self._ui = ConsoleUI(max_output_lines=32)
        self._project_selector = ProjectSelector(self._client, self._ui)
        self._task_type_selector = TaskTypeSelector(self._ui)
        self._doc_selector = DocumentReferenceSelector(self._client, self._ui)
        self._session_runner = SessionTaskRunner(
            client=self._client, config=self._config, executor=self._executor, ui=self._ui
        )
        self._store = TaskCheckpointStore(log_dir="log")
        self._event_log = TaskEventLog(log_dir="log")
        self._coordinator = ResumeCoordinator(self._store)
        self._runner = RecoverableTaskRunner(
            client=self._client,
            config=self._config,
            executor=self._executor,
            store=self._store,
            coordinator=self._coordinator,
            event_log=self._event_log,
        )
        self._store.mark_all_interrupted_on_startup(source="console")

    def run(self) -> None:
        self._ui.set_title("agentCoderGroup Console (Ctrl+Enter to send)")
        self._check_and_resume_interrupted()
        while True:
            project = self._project_selector.select_or_create()
            if project is None:
                self._ui.append_output("Exit command received. Bye.")
                self._ui.render()
                return
            self._project_menu(project)

    def _check_and_resume_interrupted(self) -> None:
        import time

        snapshots = self._coordinator.list_unfinished(source="console")
        if not snapshots:
            return

        lines = ["=== Unfinished Tasks Detected ==="]
        for i, snap in enumerate(snapshots, 1):
            project_name = snap.project.get('name', '?') if snap.project else snap.project_id
            lines.append(f"  {i}. Task ID: {snap.task_id} | Type: {snap.task_type} | Project: {project_name} | Stage: {snap.current_stage} | State: {snap.state}")
        lines.append("  s. Skip and start new task")

        self._ui.set_output(lines)
        self._ui.set_info(["Select a task to resume, or 's' to skip."])

        selected_snap = None
        while True:
            choice = self._ui.prompt_input("Select task index (or s to skip): ")
            if ConsoleUI.is_exit_command(choice):
                raise SystemExit(0)
            if choice.strip().lower() in {'s', 'skip'}:
                return
            
            try:
                idx = int(choice.strip()) - 1
                if 0 <= idx < len(snapshots):
                    selected_snap = snapshots[idx]
                    break
                else:
                    self._ui.append_output("Invalid index.")
            except ValueError:
                self._ui.append_output("Please enter a number or 's'.")

        snap = selected_snap
        self._ui.append_output(f"Resuming Task ID: {snap.task_id}")

        self._runner.resume_task(task_id=snap.task_id, progress_callback=self._build_console_progress_callback())

        if snap.pending_user_input:
            agent_name = str(snap.pending_user_input.get("agent_name", "agent"))
            latest_reply = str(snap.pending_user_input.get("latest_reply", ""))
            self._ui.append_output(f"[{agent_name}] {latest_reply}")
            reply = self._ui.prompt_input(f"{agent_name}> ")
            if ConsoleUI.is_exit_command(reply):
                raise SystemExit(0)
            self._runner.send_user_reply(snap.task_id, reply)

        self._ui.append_output(f"Task {snap.task_id} resumed. Monitoring progress...")
        while True:
            cur = self._store.load(snap.task_id)
            if cur is None or cur.state in ("done", "error"):
                if cur and cur.state == "error":
                    self._ui.append_output(f"=== Task Failed: {cur.error_reason} ===")
                elif cur:
                    self._ui.append_output("=== Task Completed Successfully ===")
                return
            if cur.state == "waiting_input" and cur.pending_user_input:
                agent_name = str(cur.pending_user_input.get("agent_name", "agent"))
                latest_reply = str(cur.pending_user_input.get("latest_reply", ""))
                self._ui.append_output(f"[{agent_name}] {latest_reply}")
                reply = self._ui.prompt_input(f"{agent_name}> ")
                if ConsoleUI.is_exit_command(reply):
                    raise SystemExit(0)
                self._runner.send_user_reply(snap.task_id, reply)
            time.sleep(2)

    def _build_console_progress_callback(self):
        def cb(event):
            self._ui.append_output(f"[{event.agent}] {event.message}")

        return cb

    def _project_menu(self, project: dict) -> None:
        while True:
            convs = self._client.list_conversations(project["id"])
            lines = ["Conversations:", "  0. New coding session"]
            for i, c in enumerate(convs, 1):
                lines.append(f"  {i}. {c.get('name', 'unnamed')}")
            lines.append("  b. Back to project list")
            self._ui.set_output(lines)
            self._ui.set_info(
                [
                    f"Current project: {project.get('name')} (id={project.get('id')})",
                    "Input 0 to create coding session",
                    "Input conversation index to chat",
                    "Input b to back",
                ]
            )

            choice = self._ui.prompt_input("Select conversation: ")
            if ConsoleUI.is_exit_command(choice):
                raise SystemExit(0)
            if choice.lower() == "b":
                return
            if choice == "0":
                self._run_new_session(project)
                continue

            try:
                conv = convs[int(choice) - 1]
                self._chat_existing_conversation(project, conv)
            except (ValueError, IndexError):
                self._ui.append_output("Invalid conversation selection.")

    def _run_new_session(self, project: dict) -> None:
        conv_name = self._ui.prompt_input("Conversation name: ")
        if ConsoleUI.is_exit_command(conv_name):
            raise SystemExit(0)

        task_type = self._task_type_selector.select()
        conversation_id = self._create_task_conversation(int(project["id"]), conv_name, task_type)
        if not conversation_id:
            return

        selected_doc_ids = self._doc_selector.choose_conversation_level_references(
            int(project["id"]), conversation_id
        )
        if selected_doc_ids:
            try:
                self._client.set_conversation_document_references(conversation_id, selected_doc_ids)
                self._ui.append_output(
                    f"Conversation-level references set: {len(selected_doc_ids)} document(s)."
                )
                self._ui.append_outputs(
                    self._doc_selector.render_references_for_conversation(
                        int(project["id"]), conversation_id
                    )
                )
            except ChatBackendError as exc:
                self._ui.append_output(f"Set conversation-level references failed: {exc}")
        else:
            self._ui.append_output("Conversation-level references skipped.")
            self._ui.append_outputs(
                self._doc_selector.render_references_for_conversation(
                    int(project["id"]), conversation_id
                )
            )

        requirement = self._prompt_task_input(task_type)
        if ConsoleUI.is_exit_command(requirement):
            raise SystemExit(0)

        final = self._session_runner.run(
            project=project,
            conv_name=conv_name,
            task_type=task_type,
            requirement=requirement,
            conversation_document_ids=selected_doc_ids,
            existing_conversation_id=conversation_id,
        )
        self._print_final_result(final)

    def _create_task_conversation(self, project_id: int, conv_name: str, task_type: TaskType) -> str | None:
        agent_key = get_agent_key_for_task_type(task_type)
        cfg = getattr(self._config, agent_key)
        try:
            prompt = load_prompt(cfg.prompt_file)
            return self._client.create_conversation(
                project_id=project_id,
                name=conv_name,
                system_prompt=prompt,
                model=cfg.model,
                assistance_role=agent_key,
            )
        except ChatBackendError as exc:
            self._ui.append_output(f"Create conversation failed: {exc}")
            return None

    def _prompt_task_input(self, task_type: TaskType) -> str:
        if task_type == "formal_dev":
            return self._ui.prompt_input("Formal development document: ")
        if task_type == "code_change":
            return self._ui.prompt_input("Change request / bug description: ")
        return self._ui.prompt_input("Coding requirement: ")

    def _chat_existing_conversation(self, project: dict, conv: dict) -> None:
        model = conv.get("model") or self._config.architect.model
        self._ui.set_output(
            self._doc_selector.render_references_for_conversation(int(project["id"]), conv["id"])
        )
        self._ui.set_info(["Reference preview before chat.", "Input /back to return."])
        self._ui.render()
        self._ui.append_output("Interactive mode. /back to return.")
        while True:
            msg = self._ui.prompt_input("You: ")
            if ConsoleUI.is_exit_command(msg):
                raise SystemExit(0)
            if msg.strip().lower() == "/back":
                return
            if not msg:
                self._ui.append_output("Message cannot be empty.")
                continue
            reply = self._client.send_message(conv["id"], msg, model)
            self._ui.append_output(f"[Reply]\n{reply}")

    def _print_final_result(self, result: FinalResult) -> None:
        self._ui.append_output("=== Task Complete ===")
        self._ui.append_output(f"Project: {result.project_name}")
        self._ui.append_output(f"Root Dir: {result.root_dir}")
        self._ui.append_output(f"Success: {result.success}")
        if result.sub_results:
            for sr in result.sub_results:
                steps = sum(pr.steps_completed for pr in sr.programmer_results)
                state = "OK" if sr.success else "FAIL"
                self._ui.append_output(f"Phase {sr.phase_id}: {state} ({steps} steps)")
        if not result.success:
            self._ui.append_output(f"Error Node: {result.error_node}")
            self._ui.append_output(f"Error Reason: {result.error_reason}")
        if result.usage_hint:
            self._ui.append_output(f"Usage: {result.usage_hint}")


def main():
    config = load_config()
    ConsoleRunner(config).run()


if __name__ == "__main__":
    main()
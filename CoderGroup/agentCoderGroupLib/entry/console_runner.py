from ..adapters.chat_backend_client import ChatBackendClient
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..agents.architect_agent import ArchitectAgent
from ..config.app_config import AppConfig, load_config
from ..config.constants import GO_ON_PROMPT
from ..orchestrator.engineer_loop import EngineerLoop
from ..orchestrator.programmer_loop import ProgrammerLoop
from ..orchestrator.task_router import TaskRouter
from ..reporting.progress_reporter import ProgressReporter
from ..reporting.result_models import FinalResult


def requires_user_input(reply: str) -> bool:
    lines = reply.splitlines()
    last_lines = lines[-3:] if len(lines) >= 3 else lines
    return (
        any("?" in l for l in last_lines)
        or "[Awaiting confirmation]" in reply
        or "please confirm" in reply.lower()
        or "do you want" in reply.lower()
    )


class ConsoleRunner:
    def __init__(self, config: AppConfig):
        self._config = config
        self._client = ChatBackendClient(config.chat_backend_url, config.chat_backend_token)
        self._reporter = ProgressReporter(mode="console")
        self._executor = CodeExecutorAdapter()

    def run(self) -> None:
        projects = self._client.list_projects()
        if not projects:
            print("No projects found.")
            return

        print("\n=== Projects ===")
        for i, p in enumerate(projects, 1):
            print(f"  {i}. {p['name']} (id={p['id']})")

        try:
            choice = int(input("\nSelect project number: ")) - 1
            project = projects[choice]
        except (ValueError, IndexError):
            print("Invalid selection.")
            return

        print(f"\nSelected: {project['name']}")

        convs = self._client.list_conversations(project["id"])
        print("\n=== Conversations ===")
        print("  0. New conversation")
        for i, c in enumerate(convs, 1):
            print(f"  {i}. {c['name']} (updated: {c.get('updated_at', 'N/A')})")

        try:
            conv_choice = int(input("\nSelect conversation (0 for new): "))
        except ValueError:
            print("Invalid selection.")
            return

        if conv_choice == 0:
            conv_name = input("Conversation name: ").strip()
            requirement = input("Coding requirement: ").strip()
            self._run_new_session(project, conv_name, requirement)
        else:
            try:
                conv = convs[conv_choice - 1]
            except IndexError:
                print("Invalid selection.")
                return
            message = input("Your message: ").strip()
            reply = self._client.send_message(
                conv["id"], message, self._config.architect.model
            )
            print(f"\n[Reply]\n{reply}")

    def _run_new_session(self, project: dict, conv_name: str, requirement: str) -> None:
        project_id = project["id"]

        docs = self._client.get_knowledge_docs(project_id)
        knowledge_block = ""
        for doc in docs:
            filename = doc.get("filename", "doc")
            content = doc.get("content", "")
            knowledge_block += (
                f"----- {filename} BEGIN -----\n{content}\n----- {filename} END -----\n\n"
            )

        first_message = (knowledge_block + requirement).strip()

        self._reporter.emit("status", "ArchitectAgent", "Starting architect phase...")
        architect = ArchitectAgent(self._client, self._config, project_id, conv_name)

        reply = architect.send(first_message)
        self._reporter.emit_line_count("ArchitectAgent", reply)

        while not architect.is_complete(reply):
            if requires_user_input(reply):
                user_response = input("Your response: ").strip()
                reply = architect.send(user_response)
            else:
                reply = architect.send(GO_ON_PROMPT)
            self._reporter.emit_line_count("ArchitectAgent", reply)

        file_count = architect.extract_file_count(reply)
        task_doc = architect.get_task_document()
        self._reporter.emit(
            "status", "ArchitectAgent", f"Architect complete. Estimated files: {file_count}"
        )

        router = TaskRouter(self._config.max_files_per_run)
        route = router.route(file_count)
        self._reporter.emit("status", "TaskRouter", f"Routing to: {route}")

        if route == "programmer":
            loop = ProgrammerLoop(self._client, self._config, self._executor, self._reporter)
            result = loop.run(task_doc, project)
            final = FinalResult(
                task_id=architect.conversation_id,
                success=result.success,
                root_dir=result.root_dir,
                project_name=project["name"],
                sub_results=[],
                error_node=result.error_node,
                error_reason=result.error_reason,
            )
        else:
            loop = EngineerLoop(self._client, self._config, self._executor, self._reporter)
            sub_results = loop.run(task_doc, project)
            success = all(r.success for r in sub_results)
            failed = next((r for r in sub_results if not r.success), None)
            root_dir = project.get("ai_work_dir", ".")
            final = FinalResult(
                task_id=architect.conversation_id,
                success=success,
                root_dir=root_dir,
                project_name=project["name"],
                sub_results=sub_results,
                error_node=failed.error_node if failed else None,
                error_reason=failed.error_reason if failed else None,
            )

        self._print_final_result(final)

    def _print_final_result(self, result: FinalResult) -> None:
        print("\n=== Task Complete ===")
        print(f"Project  : {result.project_name}")
        print(f"Root Dir : {result.root_dir}")
        print(f"Success  : {result.success}")

        if result.sub_results:
            print("\nCompleted Sub-tasks:")
            for sr in result.sub_results:
                status = "v" if sr.success else "x"
                steps = sum(pr.steps_completed for pr in sr.programmer_results)
                print(f"  [Phase {sr.phase_id}] {status} {steps} steps")

        if not result.success and result.error_node:
            print(f"\nError Node    : conversation/{result.error_node}")
            print(f"Error Reason  : {result.error_reason}")

        if result.usage_hint:
            print(f"\nUsage:\n  {result.usage_hint}")


def main():
    config = load_config()
    runner = ConsoleRunner(config)
    runner.run()


if __name__ == "__main__":
    main()

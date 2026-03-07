from ..adapters.chat_backend_client import ChatBackendClient, ChatBackendError
from .console_ui import ConsoleUI
from .document_reference_selector import DocumentReferenceSelector
from .project_pagination import ProjectPaginator


class ProjectSelector:
    def __init__(self, client: ChatBackendClient, ui: ConsoleUI):
        self._client = client
        self._ui = ui
        self._doc_selector = DocumentReferenceSelector(client, ui)

    def select_or_create(self) -> dict | None:
        page = 1
        while True:
            projects = self._client.list_projects()
            paginator = ProjectPaginator(projects=projects, page_size=18, columns=3, name_width=24)
            page = paginator.clamp_page(page)

            output_lines = paginator.render_page_lines(page)
            output_lines.extend(
                [
                    "",
                    "Commands:",
                    "  s <index> / <index>  -> select project",
                    "  n / next             -> next page",
                    "  p / prev             -> previous page",
                    "  g <page>             -> goto page",
                    "  new                  -> create project",
                ]
            )
            self._ui.set_output(output_lines)
            self._ui.set_info(
                [
                    "Project selection",
                    "Long lists are shown in multiple columns with pagination",
                    "All inputs are multiline; Ctrl+Enter sends",
                ]
            )

            cmd = self._ui.prompt_input("Project command: ")
            if ConsoleUI.is_exit_command(cmd):
                return None

            action, value = paginator.parse_paging_command(cmd)

            if action == "next":
                page = paginator.clamp_page(page + 1)
                continue
            if action == "prev":
                page = paginator.clamp_page(page - 1)
                continue
            if action == "goto":
                if value is None:
                    self._ui.append_output("Missing page number.")
                    continue
                page = paginator.clamp_page(value)
                continue
            if action == "new":
                project = self._create_project()
                if project is None:
                    continue
                return project
            if action == "select":
                if value is None:
                    self._ui.append_output("Missing project index.")
                    continue
                idx = value - 1
                if idx < 0 or idx >= len(projects):
                    self._ui.append_output("Project index out of range.")
                    continue
                return projects[idx]

            self._ui.append_output("Unknown command.")

    def _create_project(self) -> dict | None:
        name = self._ui.prompt_input("Project name: ")
        if ConsoleUI.is_exit_command(name):
            return None
        if not name:
            self._ui.append_output("Project name cannot be empty.")
            return None

        default_dir = f"/aiWorkDir/{name}"
        ai_work_dir = self._ui.prompt_input(f"ai_work_dir (default: {default_dir}): ")
        if ConsoleUI.is_exit_command(ai_work_dir):
            return None
        ai_work_dir = ai_work_dir or default_dir

        try:
            project = self._client.create_project(name=name, ai_work_dir=ai_work_dir)
            self._ui.append_output(
                f"Project created: {project.get('name', 'unknown')} (id={project.get('id', 'N/A')})"
            )
        except ChatBackendError as exc:
            self._ui.append_output(f"Create project failed: {exc}")
            return None

        project_id = int(project.get("id", 0) or 0)
        selected_ids = self._doc_selector.choose_project_level_references(project_id)
        if selected_ids:
            try:
                self._client.set_project_document_references(project_id, selected_ids)
                self._ui.append_output(f"Project-level references set: {len(selected_ids)} document(s).")
                self._ui.append_outputs(self._doc_selector.render_project_references(project_id))
            except ChatBackendError as exc:
                self._ui.append_output(f"Set project-level references failed: {exc}")
        else:
            self._ui.append_output("Project-level references skipped.")
        return project
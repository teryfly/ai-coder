from ..config.task_types import DEFAULT_TASK_TYPE, TASK_TYPE_OPTIONS, TaskType, normalize_task_type
from .console_ui import ConsoleUI


class TaskTypeSelector:
    def __init__(self, ui: ConsoleUI):
        self._ui = ui

    def select(self) -> TaskType:
        lines = ["Task Type Selection:"]
        for option in TASK_TYPE_OPTIONS:
            lines.append(f"  {option.key}. {option.title}")
            lines.append(f"     - {option.description}")

        lines.extend(
            [
                "",
                "Input: A/B/C (or new_dev/formal_dev/code_change)",
                f"Default: {DEFAULT_TASK_TYPE}",
            ]
        )

        self._ui.set_output(lines)
        self._ui.set_info(
            [
                "Choose one task type for the new conversation.",
                "A -> Architect flow, B -> Engineer flow, C -> Programmer flow.",
            ]
        )

        text = self._ui.prompt_input("Task type: ")
        if ConsoleUI.is_exit_command(text):
            raise SystemExit(0)

        return normalize_task_type(text)
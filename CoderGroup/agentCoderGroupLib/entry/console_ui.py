from collections import deque
from typing import Iterable

from .multiline_input import MultilineInput


class ConsoleUI:
    def __init__(self, max_output_lines: int = 24):
        self._output_lines: deque[str] = deque(maxlen=max_output_lines)
        self._info_lines: list[str] = []
        self._title: str = "agentCoderGroup Console"
        self._input = MultilineInput()

    def set_title(self, title: str) -> None:
        self._title = title

    def set_info(self, lines: Iterable[str]) -> None:
        self._info_lines = [str(x) for x in lines]

    def clear_output(self) -> None:
        self._output_lines.clear()

    def set_output(self, lines: Iterable[str]) -> None:
        self._output_lines.clear()
        for line in lines:
            self._output_lines.append(str(line))

    def append_output(self, line: str) -> None:
        self._output_lines.append(str(line))

    def append_outputs(self, lines: Iterable[str]) -> None:
        for line in lines:
            self._output_lines.append(str(line))

    def render(self) -> None:
        print("\033[2J\033[H", end="")
        print(f"=== {self._title} ===")
        print("-" * 72)
        print("[Output]")
        if not self._output_lines:
            print("(empty)")
        else:
            for line in self._output_lines:
                print(line)

        print("-" * 72)
        print("[Info]")
        if not self._info_lines:
            print("(empty)")
        else:
            for line in self._info_lines:
                print(line)

        print("-" * 72)
        print("[Input]")
        print("Multi-line mode. Press Ctrl+Enter to send.")
        print("Exit commands: /exit | exit | quit | q")
        print("-" * 72)

    def prompt_input(self, prompt: str = "> ") -> str:
        self.render()
        return self._input.read_multiline(prompt).strip()

    @staticmethod
    def is_exit_command(text: str) -> bool:
        return text.strip().lower() in {"/exit", "exit", "quit", "q"}
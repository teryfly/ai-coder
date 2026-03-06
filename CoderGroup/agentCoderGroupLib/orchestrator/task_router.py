from typing import Literal


class TaskRouter:
    def __init__(self, max_files_per_run: int):
        self._max_files = max_files_per_run

    def route(self, file_count: int) -> Literal["programmer", "engineer"]:
        return "programmer" if file_count < self._max_files else "engineer"

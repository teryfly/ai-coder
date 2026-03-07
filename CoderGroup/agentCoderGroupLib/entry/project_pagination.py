from dataclasses import dataclass
from math import ceil
from typing import Iterable


@dataclass(frozen=True)
class ProjectItem:
    index: int
    project_id: int
    name: str


@dataclass(frozen=True)
class ProjectPage:
    page: int
    total_pages: int
    items: list[ProjectItem]


class ProjectPaginator:
    """
    Render long project lists in paged multi-column text blocks.
    """

    def __init__(
        self,
        projects: Iterable[dict],
        page_size: int = 18,
        columns: int = 3,
        name_width: int = 26,
    ):
        self._raw_projects = list(projects)
        self._page_size = max(1, page_size)
        self._columns = max(1, columns)
        self._name_width = max(12, name_width)

        self._items: list[ProjectItem] = []
        for i, p in enumerate(self._raw_projects, 1):
            self._items.append(
                ProjectItem(
                    index=i,
                    project_id=int(p.get("id", 0) or 0),
                    name=str(p.get("name", "unknown")),
                )
            )

    @property
    def total_items(self) -> int:
        return len(self._items)

    @property
    def total_pages(self) -> int:
        if not self._items:
            return 1
        return ceil(len(self._items) / self._page_size)

    def clamp_page(self, page: int) -> int:
        return min(max(1, page), self.total_pages)

    def get_page(self, page: int) -> ProjectPage:
        page = self.clamp_page(page)
        start = (page - 1) * self._page_size
        end = start + self._page_size
        return ProjectPage(page=page, total_pages=self.total_pages, items=self._items[start:end])

    def render_page_lines(self, page: int) -> list[str]:
        data = self.get_page(page)
        lines: list[str] = []
        lines.append(
            f"Projects (page {data.page}/{data.total_pages}, total: {self.total_items})"
        )

        if not data.items:
            lines.append("  (no projects)")
            return lines

        rows = ceil(len(data.items) / self._columns)
        matrix: list[list[ProjectItem | None]] = [
            [None for _ in range(self._columns)] for _ in range(rows)
        ]

        for i, item in enumerate(data.items):
            r = i % rows
            c = i // rows
            if c < self._columns:
                matrix[r][c] = item

        col_width = self._name_width + 18
        for r in range(rows):
            row_chunks: list[str] = []
            for c in range(self._columns):
                item = matrix[r][c]
                if item is None:
                    row_chunks.append("".ljust(col_width))
                    continue
                idx = str(item.index).rjust(3)
                pid = str(item.project_id).rjust(4)
                name = self._truncate(item.name, self._name_width)
                text = f"{idx}. {name} (id={pid})"
                row_chunks.append(text.ljust(col_width))
            lines.append("".join(row_chunks).rstrip())

        return lines

    @staticmethod
    def parse_paging_command(text: str) -> tuple[str, int | None]:
        """
        Returns:
          ("next", None)  for n/next
          ("prev", None)  for p/prev
          ("goto", page)  for number page commands: g 2 / page 2
          ("select", idx) for selection commands: s 12 / select 12 / 12
          ("new", None)   for new/create/c
          ("back", None)  for b/back
          ("unknown", None)
        """
        raw = (text or "").strip().lower()
        if not raw:
            return ("unknown", None)

        if raw in {"n", "next"}:
            return ("next", None)
        if raw in {"p", "prev", "previous"}:
            return ("prev", None)
        if raw in {"b", "back"}:
            return ("back", None)
        if raw in {"new", "create", "c"}:
            return ("new", None)

        parts = raw.split()
        if len(parts) == 1 and parts[0].isdigit():
            return ("select", int(parts[0]))

        if len(parts) == 2 and parts[0] in {"s", "select"} and parts[1].isdigit():
            return ("select", int(parts[1]))

        if len(parts) == 2 and parts[0] in {"g", "page"} and parts[1].isdigit():
            return ("goto", int(parts[1]))

        return ("unknown", None)

    @staticmethod
    def _truncate(value: str, width: int) -> str:
        if len(value) <= width:
            return value
        if width <= 3:
            return value[:width]
        return value[: width - 3] + "..."
"""Data container for a text block produced by the splitter."""

from dataclasses import dataclass


@dataclass
class RawBlock:
    """Represents a text block after splitting, before parsing.

    Attributes:
        text: Raw block content, stripped of surrounding whitespace.
        offset: Character offset of block start in original text.
        line_number: Line number (1-based) of block start in original text.
    """

    text: str
    offset: int
    line_number: int

    @property
    def preview(self) -> str:
        """First 200 characters of text."""
        return self.text[:200]

    @property
    def first_lines(self) -> str:
        """First 5 lines of text, joined by newline."""
        return "\n".join(self.text.splitlines()[:5])
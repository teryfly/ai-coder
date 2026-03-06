"""Splits full input text into RawBlock instances at 6-hyphen separators."""

from ..constants import Patterns
from ..models.raw_block import RawBlock
from ..models.diagnostic import Diagnostic


class BlockSplitter:
    """Splits structured text into blocks using exact 6-hyphen separators.

    Also detects suspicious separator lines (3+ hyphens but not exactly 6)
    and reports them as diagnostics.

    All methods are static.
    """

    @staticmethod
    def split(content: str) -> list[RawBlock]:
        """Split content into RawBlock instances at 6-hyphen separators.

        Args:
            content: Full input text to split.

        Returns:
            List of RawBlock instances, each with text, offset,
            and line_number populated.
        """
        if not content or not content.strip():
            return []

        matches = list(Patterns.SEPARATOR.finditer(content))

        if not matches:
            stripped = content.strip()
            if stripped:
                line_num = BlockSplitter._line_number_at(content, 0)
                return [RawBlock(text=stripped, offset=0, line_number=line_num)]
            return []

        blocks = []
        segments = []

        first_start = matches[0].start()
        if first_start > 0:
            segments.append((0, first_start))

        for i in range(len(matches)):
            seg_start = matches[i].end()
            if i + 1 < len(matches):
                seg_end = matches[i + 1].start()
            else:
                seg_end = len(content)
            segments.append((seg_start, seg_end))

        for seg_start, seg_end in segments:
            raw_text = content[seg_start:seg_end]
            stripped = raw_text.strip()
            if not stripped:
                continue

            text_before = content[:seg_start]
            actual_offset = seg_start + (len(raw_text) - len(raw_text.lstrip()))
            line_num = BlockSplitter._line_number_at(content, actual_offset)

            blocks.append(
                RawBlock(
                    text=stripped,
                    offset=actual_offset,
                    line_number=line_num,
                )
            )

        return blocks

    @staticmethod
    def detect_suspicious_separators(content: str) -> list[Diagnostic]:
        """Find lines with 3+ hyphens that are not exactly 6-hyphen separators.

        Args:
            content: Full input text to scan.

        Returns:
            List of Diagnostic warnings for suspicious separator lines.
        """
        if not content:
            return []

        diagnostics = []

        for match in Patterns.SUSPICIOUS_SEPARATOR.finditer(content):
            line_text = match.group().strip()

            if line_text == "------":
                continue

            hyphen_count = len(line_text)
            line_num = BlockSplitter._line_number_at(
                content, match.start()
            )
            diagnostics.append(
                Diagnostic(
                    line_number=line_num,
                    message=(
                        f"Suspicious separator: {hyphen_count} hyphens "
                        f"(expected exactly 6)"
                    ),
                    severity="warning",
                )
            )

        return diagnostics

    @staticmethod
    def _line_number_at(text: str, offset: int) -> int:
        """Calculate 1-based line number at a character offset.

        Args:
            text: The full text.
            offset: Character offset position.

        Returns:
            1-based line number.
        """
        return text[:offset].count('\n') + 1
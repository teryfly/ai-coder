"""Extracts fenced code blocks with dynamic fence-level matching."""

from dataclasses import dataclass
import re

from ..constants import Patterns


@dataclass
class ExtractionResult:
    """Result of code block extraction.

    Attributes:
        blocks: List of extracted code block contents.
        count: Number of blocks extracted.
        warnings: List of warning messages.
        has_unclosed: True if an unclosed fence was recovered.
    """

    blocks: list[str]
    count: int
    warnings: list[str]
    has_unclosed: bool


class CodeBlockExtractor:
    """Extracts fenced code blocks with dynamic fence-level matching.

    Supports 3, 4, 5+ backtick fences. Recovers unclosed fences to
    end-of-text with a warning flag.

    All methods are static.
    """

    @staticmethod
    def extract(content: str) -> ExtractionResult:
        """Extract all fenced code blocks from content.

        Args:
            content: Text potentially containing fenced code blocks.

        Returns:
            ExtractionResult with blocks, count, warnings, and unclosed flag.
        """
        if not content:
            return ExtractionResult(
                blocks=[], count=0, warnings=[], has_unclosed=False
            )

        content = content.replace('\r\n', '\n')

        blocks: list[str] = []
        warnings: list[str] = []
        has_unclosed = False
        i = 0

        while i < len(content):
            fence_info = CodeBlockExtractor._scan_fence_open(content, i)
            if fence_info is None:
                break

            fence_start, fence_level, content_start = fence_info

            close_pos = CodeBlockExtractor._scan_fence_close(
                content, content_start, fence_level
            )

            if close_pos is None:
                # Unclosed fence - extract to end of text
                extracted = content[content_start:]
                blocks.append(extracted)
                warnings.append(
                    f"Unclosed code block (fence level {fence_level}) "
                    f"starting at character {fence_start}"
                )
                has_unclosed = True
                break

            # Extract content between opening fence and closing fence
            # close_pos is the start index of the closing fence line
            extracted = content[content_start:close_pos]

            # Logic to remove the specific newline that separates content from the closing fence
            # If the extracted content ends with a newline, it means there was a newline
            # right before the closing ```. This is usually structural (part of the markdown),
            # not part of the code content itself, unless the code explicitly ends with empty lines.
            
            # However, we must be careful. If the user wrote:
            # ```python
            # print("hi")
            # ```
            # The string is `print("hi")\n`. We usually want `print("hi")`.
            
            # If the user wrote:
            # ```python
            # print("hi")
            #
            # ```
            # The string is `print("hi")\n\n`. We want `print("hi")\n`.

            if extracted.endswith('\n'):
                extracted = extracted[:-1]

            blocks.append(extracted)

            # Move past the closing fence line
            newline_after_close = content.find('\n', close_pos)
            if newline_after_close == -1:
                # No more content after closing fence
                break
            i = newline_after_close + 1

        return ExtractionResult(
            blocks=blocks,
            count=len(blocks),
            warnings=warnings,
            has_unclosed=has_unclosed,
        )

    @staticmethod
    def extract_for_markdown(
        content: str, file_path_line: str
    ) -> str | None:
        """Extract markdown-fenced code block after file path line.

        Searches for the last markdown fence after the file path line
        to handle cases where multiple markdown blocks exist.

        Args:
            content: Full block text.
            file_path_line: The raw File Path line to use as anchor.

        Returns:
            Extracted markdown content or None if not found.
        """
        anchor_pos = content.find(file_path_line)
        if anchor_pos == -1:
            return None

        search_start = anchor_pos + len(file_path_line)
        remaining = content[search_start:]

        lines = remaining.split('\n')
        md_fence_start = -1
        fence_level = 0

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('```') or stripped.startswith('````'):
                backticks = len(stripped) - len(stripped.lstrip('`'))
                rest = stripped[backticks:].strip().lower()
                if rest.startswith('markdown') or rest == 'md':
                    md_fence_start = idx
                    fence_level = backticks
                    break

        if md_fence_start == -1:
            return None

        content_lines = []
        for idx in range(md_fence_start + 1, len(lines)):
            line = lines[idx]
            stripped = line.strip()
            if stripped.startswith('`' * fence_level):
                backticks = len(stripped) - len(stripped.lstrip('`'))
                if backticks == fence_level and stripped == '`' * fence_level:
                    break
            content_lines.append(line)

        return '\n'.join(content_lines)

    @staticmethod
    def _scan_fence_open(
        text: str, start_pos: int
    ) -> tuple[int, int, int] | None:
        """Scan for opening fence from start_pos.

        Args:
            text: Full text to scan.
            start_pos: Character position to start scanning.

        Returns:
            Tuple of (fence_start, fence_level, content_start) or None.
        """
        match = Patterns.FENCE_OPEN.search(text, start_pos)
        if not match:
            return None

        fence_start = match.start()
        fence_str = match.group(1).strip()
        fence_level = len(fence_str)

        if fence_level < 3:
            return None

        # Start of the code content is after the newline of the opening fence
        newline_pos = text.find('\n', match.end())
        if newline_pos == -1:
            content_start = len(text)
        else:
            content_start = newline_pos + 1

        return (fence_start, fence_level, content_start)

    @staticmethod
    def _scan_fence_close(
        text: str, start_pos: int, fence_level: int
    ) -> int | None:
        """Scan for closing fence matching fence_level.

        Args:
            text: Full text to scan.
            start_pos: Character position to start scanning.
            fence_level: Number of backticks required for closing fence.

        Returns:
            Character position of closing fence line start, or None.
        """
        # We need to find the start index of the closing fence line.
        # Simple split('\n') loses position info. We must scan manually or use find().
        
        current_pos = start_pos
        while True:
            # Find next newline to isolate a line
            newline_pos = text.find('\n', current_pos)
            
            if newline_pos == -1:
                # Last line of text
                line = text[current_pos:]
                stripped = line.strip()
                if stripped.startswith('`' * fence_level):
                    backticks = len(stripped) - len(stripped.lstrip('`'))
                    if backticks == fence_level and stripped == '`' * fence_level:
                        return current_pos
                break
            
            # Check the line we found
            line = text[current_pos:newline_pos]
            stripped = line.strip()
            if stripped.startswith('`' * fence_level):
                backticks = len(stripped) - len(stripped.lstrip('`'))
                if backticks == fence_level and stripped == '`' * fence_level:
                    return current_pos
            
            current_pos = newline_pos + 1
            
        return None
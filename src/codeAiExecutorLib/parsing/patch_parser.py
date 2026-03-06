"""Parses search/replace block format from code block content."""

from ..constants import Patterns


class PatchParser:
    """Parses patch-style search/replace blocks.

    Expected format:
        <<<< SEARCH
        original text
        ==== REPLACE
        replacement text
        >>>>

    All methods are static.
    """

    @staticmethod
    def parse(code_content: str) -> list[tuple[str, str]]:
        """Parse search/replace pairs from patch format.

        Args:
            code_content: Code block content in patch format.

        Returns:
            List of (search_text, replace_text) tuples.
        """
        if not code_content:
            return []

        lines = code_content.split('\n')
        pairs = []

        IDLE = 0
        IN_SEARCH = 1
        IN_REPLACE = 2

        state = IDLE
        search_lines = []
        replace_lines = []

        for line in lines:
            if Patterns.SEARCH_MARKER.match(line):
                state = IN_SEARCH
                search_lines = []
            elif Patterns.REPLACE_MARKER.match(line):
                state = IN_REPLACE
                replace_lines = []
            elif Patterns.END_MARKER.match(line):
                search_text = '\n'.join(search_lines)
                replace_text = '\n'.join(replace_lines)
                pairs.append((search_text, replace_text))
                state = IDLE
                search_lines = []
                replace_lines = []
            else:
                if state == IN_SEARCH:
                    search_lines.append(line)
                elif state == IN_REPLACE:
                    replace_lines.append(line)

        return pairs

    @staticmethod
    def validate(pairs: list[tuple[str, str]]) -> tuple[bool, str]:
        """Validate search/replace pairs.

        Checks:
        - At least one pair exists
        - No empty search texts
        - No duplicate search texts

        Args:
            pairs: List of (search_text, replace_text) tuples.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not pairs:
            return (False, "No search/replace pairs found")

        seen_search = set()
        for i, (search_text, replace_text) in enumerate(pairs):
            if not search_text or search_text.strip() == "":
                return (False, f"Empty search text in pair {i + 1}")

            if search_text in seen_search:
                preview = search_text[:50]
                return (False, f"Duplicate search text: '{preview}...'")

            seen_search.add(search_text)

        return (True, "Valid")
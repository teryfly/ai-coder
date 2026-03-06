"""Strips LLM assistant artifacts from input text."""

from ..constants import LLM_THINK_PATTERNS, CONTINUATION_MARKER


class Preprocessor:
    """Cleans AI-generated text by removing thinking blocks,
    reflection markers, and continuation markers.

    All methods are static.
    """

    @staticmethod
    def clean(content: str) -> tuple[str, bool]:
        """Strip LLM artifacts from input text.

        Removes thinking blocks, reflection markers, and
        trailing [to be continued] markers. Iterates until
        no further changes occur.

        Args:
            content: Raw input text, possibly containing LLM artifacts.

        Returns:
            Tuple of (cleaned_text, was_modified). was_modified is True
            if any changes were made to the original text.
        """
        if not content:
            return ("", False)

        original = content
        result = content

        changed = True
        while changed:
            changed = False
            for pattern in LLM_THINK_PATTERNS:
                new_result = pattern.sub("", result)
                if new_result != result:
                    result = new_result
                    changed = True

        result = CONTINUATION_MARKER.sub("", result)
        result = result.strip()

        return (result, result != original)
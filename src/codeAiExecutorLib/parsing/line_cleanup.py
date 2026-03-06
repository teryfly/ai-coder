"""Scoped Markdown formatting cleanup for structural lines only.

This module provides cleanup for Step / Action / File Path / Destination /
Condition / Insert Line header lines. It is NEVER applied to code block
content.
"""

import re


def clean_structural_line(line: str) -> str:
    """Clean Markdown formatting from a structural header line.

    Processing steps (in order):
    1. Strip leading # heading markers
    2. Strip leading > quote markers
    3. Strip wrapping **bold** markers
    4. Strip wrapping `code` markers
    5. Normalize full-width colon to ASCII colon
    6. Strip whitespace

    Args:
        line: A single line that may contain Markdown formatting.

    Returns:
        Cleaned line with Markdown artifacts removed.
    """
    result = re.sub(r'^\s*#{1,6}\s*', '', line)

    result = re.sub(r'^\s*(?:>+\s*)+', '', result)

    stripped = result.strip()
    if stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4:
        stripped = stripped[2:-2]
        result = stripped

    stripped = result.strip()
    if stripped.startswith('`') and stripped.endswith('`') and len(stripped) > 2:
        stripped = stripped[1:-1]
        result = stripped

    result = result.replace('\uff1a', ':')

    return result.strip()
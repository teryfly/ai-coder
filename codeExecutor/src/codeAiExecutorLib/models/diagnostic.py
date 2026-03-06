"""Diagnostic finding representation with source location."""

from dataclasses import dataclass


@dataclass
class Diagnostic:
    """Represents a diagnostic finding (warning or error) with source location.

    Attributes:
        line_number: Line number in original text.
        message: Description of the issue.
        severity: Either 'warning' or 'error'.
    """

    line_number: int
    message: str
    severity: str
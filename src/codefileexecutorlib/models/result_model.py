"""Outcome representation for any single operation."""

from dataclasses import dataclass


@dataclass
class OperationResult:
    """Represents the outcome of any single operation.

    Attributes:
        success: Whether operation succeeded.
        message: Human-readable result description.
        error: Error details if failed.
        backup_path: Path to backup file if created.
        data: Additional structured data.
    """

    success: bool
    message: str
    error: str | None = None
    backup_path: str | None = None
    data: dict | None = None
"""Evaluate conditional execution flags."""

import os


def evaluate_condition(
    condition: str | None, path: str
) -> tuple[bool, str]:
    """Evaluate whether a task should execute based on condition.

    Supports 'if_exists' and 'if_not_exists' conditions.

    Args:
        condition: Condition string or None.
        path: File/folder path to check.

    Returns:
        Tuple of (should_execute, skip_reason). If should execute,
        skip_reason is empty string.
    """
    if condition is None:
        return (True, "")

    if condition == "if_exists":
        if os.path.exists(path):
            return (True, "")
        return (False, f"Skipped: path does not exist: {path}")

    if condition == "if_not_exists":
        if not os.path.exists(path):
            return (True, "")
        return (False, f"Skipped: path already exists: {path}")

    return (True, f"Unknown condition '{condition}', executing anyway")
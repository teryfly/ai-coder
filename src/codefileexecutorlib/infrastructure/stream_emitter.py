"""Builds standardized stream message dictionaries."""

from datetime import datetime

from ..constants import StreamType


class StreamEmitter:
    """Constructs typed stream message dicts for yielding to callers.

    Every message includes 'message', 'type', and 'timestamp' keys.
    Optional keys 'step', 'total_steps', and 'data' are included
    only when their values are not None.
    """

    def info(
        self,
        message: str,
        step: int = None,
        total: int = None,
        data: dict = None,
    ) -> dict:
        """Build an info-type stream message."""
        return self._build(message, StreamType.INFO, step, total, data)

    def progress(
        self,
        message: str,
        step: int = None,
        total: int = None,
        data: dict = None,
    ) -> dict:
        """Build a progress-type stream message."""
        return self._build(message, StreamType.PROGRESS, step, total, data)

    def success(
        self,
        message: str,
        step: int = None,
        total: int = None,
        data: dict = None,
    ) -> dict:
        """Build a success-type stream message."""
        return self._build(message, StreamType.SUCCESS, step, total, data)

    def warning(
        self,
        message: str,
        step: int = None,
        total: int = None,
        data: dict = None,
    ) -> dict:
        """Build a warning-type stream message."""
        return self._build(message, StreamType.WARNING, step, total, data)

    def error(
        self,
        message: str,
        step: int = None,
        total: int = None,
        data: dict = None,
    ) -> dict:
        """Build an error-type stream message."""
        return self._build(message, StreamType.ERROR, step, total, data)

    def shell_output(
        self,
        message: str,
        step: int = None,
        total: int = None,
        data: dict = None,
    ) -> dict:
        """Build a shell_output-type stream message."""
        return self._build(
            message, StreamType.SHELL_OUTPUT, step, total, data
        )

    def summary(
        self,
        message: str,
        data: dict = None,
    ) -> dict:
        """Build a summary-type stream message."""
        return self._build(message, StreamType.SUMMARY, None, None, data)

    def _build(
        self,
        message: str,
        type_: str,
        step: int = None,
        total: int = None,
        data: dict = None,
    ) -> dict:
        """Construct a stream message dict.

        Args:
            message: Human-readable description.
            type_: One of StreamType constants.
            step: Current step number (1-based), or None.
            total: Total number of steps, or None.
            data: Additional structured data, or None.

        Returns:
            Dict with message, type, timestamp, and optional keys.
        """
        result = {
            "message": message,
            "type": type_,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        if step is not None:
            result["step"] = step
        if total is not None:
            result["total_steps"] = total
        if data is not None:
            result["data"] = data
        return result
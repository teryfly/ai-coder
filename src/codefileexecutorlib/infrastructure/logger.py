"""File-based execution logging."""

import os
from datetime import datetime


class Logger:
    """Appends timestamped log entries to an execution log file.

    A new log file is created on each instantiation with a
    timestamp-based filename in the configured log directory.
    """

    def __init__(self, log_dir: str = "log") -> None:
        """Initialize logger and create log file.

        Args:
            log_dir: Directory for log files. Created if it does not exist.
        """
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"execution_{timestamp}.log"
        self._log_file = os.path.join(log_dir, filename)

    @property
    def log_file(self) -> str:
        """Full path to the current log file."""
        return self._log_file

    def info(self, message: str, step_num: int = None) -> None:
        """Write an INFO-level log entry.

        Args:
            message: Log message text.
            step_num: Optional step number for context.
        """
        self._write("INFO", message, step_num)

    def warning(self, message: str, step_num: int = None) -> None:
        """Write a WARNING-level log entry.

        Args:
            message: Log message text.
            step_num: Optional step number for context.
        """
        self._write("WARNING", message, step_num)

    def error(self, message: str, step_num: int = None) -> None:
        """Write an ERROR-level log entry.

        Args:
            message: Log message text.
            step_num: Optional step number for context.
        """
        self._write("ERROR", message, step_num)

    def _write(
        self, level: str, message: str, step_num: int = None
    ) -> None:
        """Append a formatted log entry to the log file.

        Format: [YYYY-MM-DD HH:MM:SS] [LEVEL] [Step N] message
        The [Step N] segment is omitted if step_num is None.

        Args:
            level: Log level string (INFO, WARNING, ERROR).
            message: Log message text.
            step_num: Optional step number for context.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        step_segment = f" [Step {step_num}]" if step_num is not None else ""
        line = f"[{timestamp}] [{level}]{step_segment} {message}\n"
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(line)
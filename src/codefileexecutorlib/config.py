"""Central configuration dataclass."""

from dataclasses import dataclass


@dataclass
class ExecutorConfig:
    """Configuration for CodeExecutor.

    Attributes:
        backup_enabled: Enable file backup before destructive operations.
        allow_shell: Allow execution of shell commands.
        shell_timeout: Maximum seconds per individual shell command.
        verify_writes: If True, read back file after writing and compare.
        log_level: Minimum log level: DEBUG, INFO, WARNING, ERROR.
        log_dir: Directory for log files.
        max_file_size: Maximum file content size in bytes (default 10 MB).
        max_path_length: Maximum path character length.
        backup_dir: Custom backup directory; None uses .backup sibling.
    """

    backup_enabled: bool = True
    allow_shell: bool = True
    shell_timeout: int = 300
    verify_writes: bool = False
    log_level: str = "INFO"
    log_dir: str = "log"
    max_file_size: int = 10_485_760
    max_path_length: int = 260
    backup_dir: str | None = None
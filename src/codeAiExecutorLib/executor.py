"""Main CodeExecutor class - public API entry point."""

import os
from typing import Generator

from .config import ExecutorConfig
from .core.pipeline import ExecutionPipeline
from .core.router import TaskRouter
from .infrastructure.logger import Logger
from .infrastructure.stream_emitter import StreamEmitter
from .models.result_model import OperationResult
from .operations.backup_manager import BackupManager
from .operations.file_ops import FileOperationHandler
from .operations.folder_ops import FolderOperationHandler
from .operations.shell_executor import ShellExecutor
from .security.command_guard import CommandGuard
from .security.path_guard import PathGuard


class CodeExecutor:
    """Main executor class providing the public API.

    Orchestrates all components: parsing, security, operations,
    and streaming feedback. Provides utility methods for file
    operations and rollback.
    """

    def __init__(
        self, config: ExecutorConfig = None, root_dir: str = None
    ) -> None:
        """Initialize CodeExecutor with configuration.

        Args:
            config: Optional configuration. Uses defaults if None.
            root_dir: Optional root directory. Uses current directory if None.
        """
        self._config = config or ExecutorConfig()
        self._default_root = root_dir or os.getcwd()

        self._logger = Logger(log_dir=self._config.log_dir)
        self._stream = StreamEmitter()

        self._path_guard = None
        self._backup_mgr = None
        self._file_ops = None
        self._folder_ops = None
        self._command_guard = None
        self._shell_exec = None
        self._router = None
        self._pipeline = None

    def execute(
        self, root_dir: str, content: str, dry_run: bool = False
    ) -> Generator[dict, None, None]:
        """Execute structured task input with streaming feedback.

        Args:
            root_dir: Root directory for all file operations.
            content: Structured task input text.
            dry_run: If True, validate without executing operations.

        Yields:
            Stream message dicts for real-time progress feedback.
        """
        self._initialize_components(root_dir)

        try:
            yield from self._pipeline.run(content, dry_run)
        except Exception as e:
            yield self._stream.error(
                f"Execution failed: {str(e)}",
                data={"exception_type": type(e).__name__},
            )
            self._logger.error(f"Execution exception: {str(e)}")

    def read_file(self, root_dir: str, file_path: str) -> str:
        """Read a file's content.

        Args:
            root_dir: Root directory.
            file_path: Relative path to file from root.

        Returns:
            File content as string.

        Raises:
            Exception: If file read fails.
        """
        self._initialize_components(root_dir)

        if self._path_guard.is_absolute(file_path):
            full_path = self._path_guard.normalize(file_path)
        else:
            full_path = self._path_guard.resolve(file_path)

        if not self._path_guard.validate(full_path):
            raise ValueError(f"Path security violation: {file_path}")

        result = self._file_ops.read(full_path)

        if not result.success:
            raise Exception(result.error or result.message)

        return result.data["content"]

    def list_dir(self, root_dir: str, dir_path: str = ".") -> list[dict]:
        """List directory contents.

        Args:
            root_dir: Root directory.
            dir_path: Relative path to directory from root.

        Returns:
            List of entry dicts with name, type, and size.

        Raises:
            Exception: If directory listing fails.
        """
        self._initialize_components(root_dir)

        if self._path_guard.is_absolute(dir_path):
            full_path = self._path_guard.normalize(dir_path)
        else:
            full_path = self._path_guard.resolve(dir_path)

        if not self._path_guard.validate(full_path):
            raise ValueError(f"Path security violation: {dir_path}")

        result = self._folder_ops.list_contents(full_path)

        if not result.success:
            raise Exception(result.error or result.message)

        return result.data["entries"]

    def rollback_file(
        self, root_dir: str, file_path: str
    ) -> OperationResult:
        """Rollback a file to its most recent backup.

        Args:
            root_dir: Root directory.
            file_path: Relative path to file from root.

        Returns:
            OperationResult indicating success or failure.
        """
        self._initialize_components(root_dir)

        if self._path_guard.is_absolute(file_path):
            full_path = self._path_guard.normalize(file_path)
        else:
            full_path = self._path_guard.resolve(file_path)

        if not self._path_guard.validate(full_path):
            return OperationResult(
                success=False,
                message="Path security violation",
                error=f"Path escapes root: {file_path}",
            )

        return self._backup_mgr.rollback_to_latest(full_path)

    def _initialize_components(self, root_dir: str) -> None:
        """Initialize or reinitialize all components for a root directory.

        Args:
            root_dir: Root directory for operations.
        """
        if self._path_guard and self._path_guard.root == os.path.realpath(
            root_dir
        ):
            return

        self._path_guard = PathGuard(root_dir, self._config)
        self._backup_mgr = BackupManager(self._config)
        self._file_ops = FileOperationHandler(
            self._backup_mgr, self._config
        )
        self._folder_ops = FolderOperationHandler()
        self._command_guard = CommandGuard()
        self._shell_exec = ShellExecutor(
            self._command_guard, self._config
        )
        self._router = TaskRouter(
            self._file_ops,
            self._folder_ops,
            self._shell_exec,
            self._path_guard,
            self._config,
        )
        self._pipeline = ExecutionPipeline(
            self._config,
            self._path_guard,
            self._stream,
            self._logger,
            self._router,
        )
"""Task dispatcher with path validation and operation routing."""

import os
from typing import Generator

from ..config import ExecutorConfig
from ..constants import ActionType
from ..models.result_model import OperationResult
from ..models.task_model import TaskModel
from ..operations.file_ops import FileOperationHandler
from ..operations.folder_ops import FolderOperationHandler
from ..operations.shell_executor import ShellExecutor
from ..security.path_guard import PathGuard
from .condition import evaluate_condition


class TaskRouter:
    """Routes validated tasks to appropriate operation handlers.

    Performs security validation, path resolution, and condition
    evaluation before dispatching to file, folder, or shell handlers.
    """

    def __init__(
        self,
        file_ops: FileOperationHandler,
        folder_ops: FolderOperationHandler,
        shell_exec: ShellExecutor,
        path_guard: PathGuard,
        config: ExecutorConfig,
    ) -> None:
        """Initialize task router with operation handlers.

        Args:
            file_ops: File operation handler.
            folder_ops: Folder operation handler.
            shell_exec: Shell executor.
            path_guard: Path security validator.
            config: Executor configuration.
        """
        self._file_ops = file_ops
        self._folder_ops = folder_ops
        self._shell_exec = shell_exec
        self._path_guard = path_guard
        self._config = config

    def dispatch(
        self, task: TaskModel, dry_run: bool
    ) -> Generator[OperationResult, None, None]:
        """Dispatch a task to the appropriate handler.

        Validates content, paths, and security before execution.
        Yields OperationResult for each sub-operation.

        Args:
            task: Parsed and validated task model.
            dry_run: If True, validate without executing.

        Yields:
            OperationResult for each operation step.
        """
        is_valid, error_msg = task.validate_content()
        if not is_valid:
            yield OperationResult(
                success=False,
                message="Content validation failed",
                error=error_msg,
            )
            return

        if task.is_shell_command:
            if not self._config.allow_shell:
                yield OperationResult(
                    success=True,
                    message="Shell execution disabled, command(s) logged",
                )
                return

            if dry_run:
                yield OperationResult(
                    success=True,
                    message="Dry-run: shell commands validated",
                )
                return

            yield from self._shell_exec.execute(
                task.content, cwd=self._path_guard.root
            )
            return

        if self._path_guard.is_absolute(task.file_path):
            full_path = self._path_guard.normalize(task.file_path)
        else:
            full_path = self._path_guard.resolve(task.file_path)

        if not self._path_guard.validate(full_path):
            yield OperationResult(
                success=False,
                message="Path security violation",
                error=f"Path escapes root: {task.file_path}",
            )
            return

        if not self._path_guard.validate_path_length(full_path):
            yield OperationResult(
                success=False,
                message="Path too long",
                error=f"Exceeds {self._config.max_path_length} characters",
            )
            return

        basename = os.path.basename(full_path)
        if basename and not self._path_guard.validate_filename(basename):
            yield OperationResult(
                success=False,
                message="Unsafe filename",
                error=f"Filename contains invalid characters: {basename}",
            )
            return

        if task.requires_content and not self._path_guard.validate_content_size(
            task.content
        ):
            yield OperationResult(
                success=False,
                message="Content too large",
                error=f"Exceeds {self._config.max_file_size} bytes",
            )
            return

        dest_full_path = None
        if task.is_move_or_copy:
            if not task.destination_path:
                yield OperationResult(
                    success=False, message="Missing destination path"
                )
                return

            if self._path_guard.is_absolute(task.destination_path):
                dest_full_path = self._path_guard.normalize(
                    task.destination_path
                )
            else:
                dest_full_path = self._path_guard.resolve(
                    task.destination_path
                )

            if not self._path_guard.validate_both(
                full_path, dest_full_path
            ):
                yield OperationResult(
                    success=False,
                    message="Destination path security violation",
                )
                return

        should_execute, skip_reason = evaluate_condition(
            task.condition, full_path
        )
        if not should_execute:
            yield OperationResult(success=True, message=skip_reason)
            return

        if dry_run:
            yield OperationResult(
                success=True,
                message=f"Dry-run: {task.action} validated for {task.file_path}",
            )
            return

        if task.action == ActionType.CREATE_FILE:
            yield self._file_ops.create(full_path, task.content)
        elif task.action == ActionType.UPDATE_FILE:
            yield self._file_ops.update(full_path, task.content)
        elif task.action == ActionType.PATCH_FILE:
            yield self._file_ops.patch(
                full_path, task.search_replace_pairs
            )
        elif task.action == ActionType.APPEND_FILE:
            yield self._file_ops.append(full_path, task.content)
        elif task.action == ActionType.INSERT_FILE:
            yield self._file_ops.insert(
                full_path, task.content, task.insert_line
            )
        elif task.action == ActionType.DELETE_FILE:
            yield self._file_ops.delete(full_path)
        elif task.action == ActionType.MOVE_FILE:
            yield self._file_ops.move(full_path, dest_full_path)
        elif task.action == ActionType.COPY_FILE:
            yield self._file_ops.copy(full_path, dest_full_path)
        elif task.action == ActionType.CREATE_FOLDER:
            yield self._folder_ops.create(full_path)
        elif task.action == ActionType.DELETE_FOLDER:
            yield self._folder_ops.delete(full_path)
        else:
            yield OperationResult(
                success=False, message=f"Unknown action: {task.action}"
            )
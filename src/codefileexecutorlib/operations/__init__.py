"""Operations package - file, folder, and shell operations."""

from .file_ops import FileOperationHandler
from .folder_ops import FolderOperationHandler
from .backup_manager import BackupManager
from .shell_executor import ShellExecutor

__all__ = [
    "FileOperationHandler",
    "FolderOperationHandler",
    "BackupManager",
    "ShellExecutor",
]
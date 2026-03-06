"""File backup creation, discovery, and restoration."""

import os
import shutil
import glob
from datetime import datetime

from ..config import ExecutorConfig
from ..models.result_model import OperationResult


class BackupManager:
    """Manages file backups with timestamped naming.

    Creates backups before destructive operations, discovers
    existing backups, and supports rollback to latest backup.
    """

    def __init__(self, config: ExecutorConfig) -> None:
        """Initialize backup manager with configuration.

        Args:
            config: Executor configuration containing backup settings.
        """
        self._config = config

    def create_backup(self, path: str) -> str | None:
        """Create a timestamped backup of a file.

        Args:
            path: Path to file to back up.

        Returns:
            Path to created backup file, or None if backup was not
            created (backup disabled, file doesn't exist, or error).
        """
        if not self._config.backup_enabled:
            return None

        if not os.path.isfile(path):
            return None

        try:
            backup_dir = self._get_backup_dir(path)
            os.makedirs(backup_dir, exist_ok=True)

            basename = os.path.basename(path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{basename}.{timestamp}.bak"
            backup_path = os.path.join(backup_dir, backup_name)

            shutil.copy2(path, backup_path)
            return backup_path

        except Exception:
            return None

    def get_latest_backup(self, path: str) -> str | None:
        """Find the most recent backup for a file.

        Args:
            path: Path to the original file.

        Returns:
            Path to most recent backup, or None if no backups exist.
        """
        backup_dir = self._get_backup_dir(path)
        if not os.path.isdir(backup_dir):
            return None

        basename = os.path.basename(path)
        pattern = os.path.join(backup_dir, f"{basename}.*.bak")
        backups = glob.glob(pattern)

        if not backups:
            return None

        backups.sort(reverse=True)
        return backups[0]

    def rollback_to_latest(self, path: str) -> OperationResult:
        """Restore a file from its most recent backup.

        Args:
            path: Path to the file to restore.

        Returns:
            OperationResult indicating success or failure.
        """
        backup_path = self.get_latest_backup(path)

        if backup_path is None:
            return OperationResult(
                success=False,
                message="No backup found",
                error="No backup available for this file",
            )

        try:
            shutil.copy2(backup_path, path)
            backup_name = os.path.basename(backup_path)
            return OperationResult(
                success=True,
                message=f"Rolled back from {backup_name}",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message="Rollback failed",
                error=str(e),
            )

    def _get_backup_dir(self, file_path: str) -> str:
        """Determine backup directory for a file.

        Args:
            file_path: Path to the file being backed up.

        Returns:
            Path to backup directory.
        """
        if self._config.backup_dir:
            return self._config.backup_dir

        file_dir = os.path.dirname(file_path)
        if not file_dir:
            file_dir = "."
        return os.path.join(file_dir, ".backup")
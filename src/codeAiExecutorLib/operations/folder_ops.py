"""Directory operations."""

import os
import shutil

from ..models.result_model import OperationResult


class FolderOperationHandler:
    """Handles folder-level operations.

    Provides create, delete, and list operations for directories.
    """

    def create(self, path: str) -> OperationResult:
        """Create a directory recursively.

        Args:
            path: Path to directory to create.

        Returns:
            OperationResult indicating success or failure.
        """
        try:
            os.makedirs(path, exist_ok=True)
            return OperationResult(success=True, message="Folder created")

        except Exception as e:
            return OperationResult(
                success=False,
                message="Folder creation failed",
                error=str(e),
            )

    def delete(self, path: str) -> OperationResult:
        """Delete a directory recursively.

        Args:
            path: Path to directory to delete.

        Returns:
            OperationResult indicating success.
        """
        if not os.path.exists(path) or not os.path.isdir(path):
            return OperationResult(
                success=True,
                message="Folder does not exist, skipped",
            )

        try:
            shutil.rmtree(path)
            return OperationResult(success=True, message="Folder deleted")

        except Exception as e:
            return OperationResult(
                success=False,
                message="Folder deletion failed",
                error=str(e),
            )

    def list_contents(self, path: str) -> OperationResult:
        """List directory contents with metadata.

        Args:
            path: Path to directory to list.

        Returns:
            OperationResult with entries in data dict.
        """
        if not os.path.exists(path) or not os.path.isdir(path):
            return OperationResult(
                success=False,
                message="Path is not a directory",
                error=f"Path: {path}",
            )

        try:
            entries = []
            with os.scandir(path) as it:
                for entry in it:
                    entry_info = {
                        "name": entry.name,
                        "type": "file" if entry.is_file() else "dir",
                        "size": entry.stat().st_size
                        if entry.is_file()
                        else 0,
                    }
                    entries.append(entry_info)

            entries.sort(key=lambda e: (e["type"] != "dir", e["name"]))

            return OperationResult(
                success=True,
                message="Listed",
                data={"entries": entries, "count": len(entries)},
            )

        except Exception as e:
            return OperationResult(
                success=False,
                message="List failed",
                error=str(e),
            )
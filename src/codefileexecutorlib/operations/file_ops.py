"""All file-level operations."""
import os
import shutil
from ..config import ExecutorConfig
from ..models.result_model import OperationResult
from .backup_manager import BackupManager
from .write_verifier import verify_written_content
class FileOperationHandler:
    """Handles all file-level operations with backup and verification support.
    Provides create, update, patch, append, insert, delete, move, copy,
    and read operations. Automatically creates parent directories and
    optionally backs up files before destructive operations.
    """
    def __init__(
        self, backup_mgr: BackupManager, config: ExecutorConfig
    ) -> None:
        """Initialize file operation handler.
        Args:
            backup_mgr: Backup manager for file backups.
            config: Executor configuration for operation settings.
        """
        self._backup_mgr = backup_mgr
        self._config = config
    def _normalize_path(self, path: str) -> str:
        """Normalize path for consistent comparison across operations.
        On Windows, this ensures consistent path separators and case handling.
        Args:
            path: Path to normalize.
        Returns:
            Normalized absolute path.
        """
        # Convert to absolute path first
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        # Normalize path separators and resolve any .. or . components
        return os.path.normpath(path)
    def create(self, path: str, content: str) -> OperationResult:
        """Create a new file with content.
        Args:
            path: Path to file to create.
            content: File content.
        Returns:
            OperationResult indicating success or failure.
        """
        try:
            # Normalize path for consistent handling
            path = self._normalize_path(path)
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            # Preserve content exactly; do not alter last line endings.
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            if self._config.verify_writes:
                is_valid, msg = verify_written_content(path, content)
                if not is_valid:
                    return OperationResult(
                        success=False,
                        message="File creation verification failed",
                        error=msg,
                    )
            return OperationResult(success=True, message="File created")
        except Exception as e:
            return OperationResult(
                success=False,
                message="File creation failed",
                error=str(e),
            )
    def update(self, path: str, content: str) -> OperationResult:
        """Update (overwrite) a file with new content.
        Args:
            path: Path to file to update.
            content: New file content.
        Returns:
            OperationResult with backup_path if backup was created.
        """
        try:
            # Normalize path for consistent handling
            path = self._normalize_path(path)
            backup_path = self._backup_mgr.create_backup(path)
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            # Preserve content exactly; do not alter last line endings.
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            if self._config.verify_writes:
                is_valid, msg = verify_written_content(path, content)
                if not is_valid:
                    if backup_path:
                        shutil.copy2(backup_path, path)
                    return OperationResult(
                        success=False,
                        message="File update verification failed",
                        error=msg,
                    )
            return OperationResult(
                success=True,
                message="File updated",
                backup_path=backup_path,
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message="File update failed",
                error=str(e),
            )
    def patch(
        self, path: str, pairs: list[tuple[str, str]]
    ) -> OperationResult:
        """Apply search/replace pairs to a file.
        Args:
            path: Path to file to patch.
            pairs: List of (search_text, replace_text) tuples.
        Returns:
            OperationResult with backup_path if backup was created.
        """
        # Normalize path for consistent handling
        path = self._normalize_path(path)
        if not os.path.isfile(path):
            return OperationResult(
                success=False,
                message="File not found for patching",
                error=f"Path: {path}",
            )
        try:
            backup_path = self._backup_mgr.create_backup(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            for search_text, replace_text in pairs:
                if search_text not in content:
                    return OperationResult(
                        success=False,
                        message="Search text not found in file",
                        error=f"Search: '{search_text[:80]}...'",
                    )
                content = content.replace(search_text, replace_text, 1)
            # Preserve exact resulting content
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            if self._config.verify_writes:
                is_valid, msg = verify_written_content(path, content)
                if not is_valid:
                    return OperationResult(
                        success=False,
                        message="Patch verification failed",
                        error=msg,
                    )
            return OperationResult(
                success=True,
                message=f"Patched {len(pairs)} section(s)",
                backup_path=backup_path,
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message="File patch failed",
                error=str(e),
            )
    def append(self, path: str, content: str) -> OperationResult:
        """Append content to a file.
        Args:
            path: Path to file to append to.
            content: Content to append.
        Returns:
            OperationResult with backup_path if file existed.
        """
        try:
            # Normalize path for consistent handling
            path = self._normalize_path(path)
            backup_path = None
            combined_content = content
            if os.path.isfile(path):
                backup_path = self._backup_mgr.create_backup(path)
                with open(path, "r", encoding="utf-8") as f:
                    existing = f.read()
                # Keep original behavior: add newline between blocks.
                combined_content = existing + "\n" + content
            else:
                parent_dir = os.path.dirname(path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(combined_content)
            return OperationResult(
                success=True,
                message="Content appended",
                backup_path=backup_path,
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message="File append failed",
                error=str(e),
            )
    def insert(
        self, path: str, content: str, line_number: int
    ) -> OperationResult:
        """Insert content at a specific line number.
        Args:
            path: Path to file to insert into.
            content: Content to insert.
            line_number: 1-based line number for insertion.
        Returns:
            OperationResult with backup_path.
        """
        # Normalize path for consistent handling
        path = self._normalize_path(path)
        if not os.path.isfile(path):
            return OperationResult(
                success=False,
                message="File not found for insert",
                error=f"Path: {path}",
            )
        try:
            backup_path = self._backup_mgr.create_backup(path)
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if line_number < 1 or line_number > len(lines) + 1:
                return OperationResult(
                    success=False,
                    message="Invalid line number",
                    error=f"Line {line_number} out of range (1-{len(lines) + 1})",
                )
            insert_lines = content.splitlines(keepends=True)
            if insert_lines and not insert_lines[-1].endswith('\n'):
                insert_lines[-1] += '\n'
            lines[line_number - 1:line_number - 1] = insert_lines
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.writelines(lines)
            return OperationResult(
                success=True,
                message=f"Inserted at line {line_number}",
                backup_path=backup_path,
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message="File insert failed",
                error=str(e),
            )
    def delete(self, path: str) -> OperationResult:
        """Delete a file.
        Args:
            path: Path to file to delete.
        Returns:
            OperationResult indicating success.
        """
        # Normalize path for consistent handling
        path = self._normalize_path(path)
        # Check if file exists using multiple methods to handle Windows path issues
        file_exists = False
        if os.path.isfile(path):
            file_exists = True
        else:
            # Try case-insensitive check on Windows
            if os.name == 'nt':
                parent = os.path.dirname(path)
                if os.path.isdir(parent):
                    basename = os.path.basename(path)
                    try:
                        for entry in os.listdir(parent):
                            if entry.lower() == basename.lower():
                                file_exists = True
                                # Use the actual filename from the filesystem
                                path = os.path.join(parent, entry)
                                break
                    except (OSError, PermissionError):
                        pass
        if not file_exists:
            return OperationResult(
                success=True,
                message="File does not exist, skipped",
            )
        try:
            self._backup_mgr.create_backup(path)
            os.remove(path)
            return OperationResult(success=True, message="File deleted")
        except Exception as e:
            return OperationResult(
                success=False,
                message="File deletion failed",
                error=str(e),
            )
    def move(self, source: str, dest: str) -> OperationResult:
        """Move (rename) a file.
        Args:
            source: Source file path.
            dest: Destination file path.
        Returns:
            OperationResult indicating success.
        """
        # Normalize paths for consistent handling
        source = self._normalize_path(source)
        dest = self._normalize_path(dest)
        if not os.path.isfile(source):
            return OperationResult(
                success=False,
                message="Source file not found",
                error=f"Path: {source}",
            )
        try:
            self._backup_mgr.create_backup(source)
            dest_dir = os.path.dirname(dest)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
            shutil.move(source, dest)
            return OperationResult(
                success=True,
                message=f"Moved to {dest}",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message="File move failed",
                error=str(e),
            )
    def copy(self, source: str, dest: str) -> OperationResult:
        """Copy a file.
        Args:
            source: Source file path.
            dest: Destination file path.
        Returns:
            OperationResult indicating success.
        """
        # Normalize paths for consistent handling
        source = self._normalize_path(source)
        dest = self._normalize_path(dest)
        if not os.path.isfile(source):
            return OperationResult(
                success=False,
                message="Source file not found",
                error=f"Path: {source}",
            )
        try:
            dest_dir = os.path.dirname(dest)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(source, dest)
            return OperationResult(
                success=True,
                message=f"Copied to {dest}",
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message="File copy failed",
                error=str(e),
            )
    def read(self, path: str) -> OperationResult:
        """Read file content.
        Args:
            path: Path to file to read.
        Returns:
            OperationResult with content in data dict.
        """
        # Normalize path for consistent handling
        path = self._normalize_path(path)
        if not os.path.isfile(path):
            return OperationResult(
                success=False,
                message="File not found",
                error=f"Path: {path}",
            )
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            line_count = len(content.splitlines())
            byte_size = len(content.encode("utf-8"))
            return OperationResult(
                success=True,
                message="File read",
                data={
                    "content": content,
                    "lines": line_count,
                    "size": byte_size,
                },
            )
        except Exception as e:
            return OperationResult(
                success=False,
                message="File read failed",
                error=str(e),
            )
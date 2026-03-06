"""Path resolution, normalization, and security validation."""

import os
import re

from ..config import ExecutorConfig
from ..constants import Patterns


class PathGuard:
    """Validates and resolves file paths against a root directory.

    Uses os.path.realpath() to resolve symlinks and prevent
    path traversal attacks. All paths must resolve to within
    the configured root directory.

    Attributes:
        root: The resolved real path of the root directory.
    """

    def __init__(self, root_dir: str, config: ExecutorConfig) -> None:
        """Initialize PathGuard with root directory and config.

        Args:
            root_dir: The root directory all paths must be within.
            config: Executor configuration for limits.
        """
        self._root_real = os.path.realpath(root_dir)
        self._config = config
        self._is_windows = os.name == "nt"

    @property
    def root(self) -> str:
        """The resolved real path of the root directory."""
        return self._root_real

    def resolve(self, relative_path: str) -> str:
        """Resolve a relative path against the root directory.

        Args:
            relative_path: Path relative to root directory.

        Returns:
            Normalized absolute path.
        """
        normalized = self._normalize_separators(relative_path)
        joined = os.path.join(self._root_real, normalized)
        return os.path.normpath(joined)

    def validate(self, absolute_path: str) -> bool:
        """Check that a path resolves to within the root directory.

        Uses os.path.realpath() to resolve symlinks before checking.

        Args:
            absolute_path: The absolute path to validate.

        Returns:
            True if path is within root, False otherwise.
        """
        real = os.path.realpath(absolute_path)
        if real == self._root_real:
            return True
        return real.startswith(self._root_real + os.sep)

    def validate_both(self, source: str, dest: str) -> bool:
        """Validate that both source and destination are within root.

        Args:
            source: Source absolute path.
            dest: Destination absolute path.

        Returns:
            True if both paths are within root.
        """
        return self.validate(source) and self.validate(dest)

    def is_absolute(self, path: str) -> bool:
        """Check if a path is absolute.

        Handles Windows drive letters, UNC paths, and Unix absolute paths.

        Args:
            path: The path to check.

        Returns:
            True if path is absolute.
        """
        if self._is_windows:
            if re.match(r'^[a-zA-Z]:[\\/]', path):
                return True
            if path.startswith('\\\\') or path.startswith('//'):
                return True
            return False
        return path.startswith('/')

    def validate_filename(self, name: str) -> bool:
        """Check if a filename contains only safe characters.

        Safe characters: word characters, dots, and hyphens.

        Args:
            name: The filename to validate (basename only).

        Returns:
            True if filename is safe.
        """
        return bool(Patterns.SAFE_FILENAME.match(name))

    def validate_path_length(self, path: str) -> bool:
        """Check that path length does not exceed configured maximum.

        Args:
            path: The full path to check.

        Returns:
            True if path length is within limit.
        """
        return len(path) <= self._config.max_path_length

    def validate_content_size(self, content: str) -> bool:
        """Check that content size does not exceed configured maximum.

        Normalizes line endings before measuring byte size.

        Args:
            content: The file content to check.

        Returns:
            True if content size is within limit.
        """
        normalized = content.replace('\r\n', '\n')
        byte_size = len(normalized.encode('utf-8'))
        return byte_size <= self._config.max_file_size

    def normalize(self, path: str) -> str:
        """Normalize path separators for the current OS.

        Args:
            path: The path to normalize.

        Returns:
            OS-appropriate normalized path.
        """
        result = self._normalize_separators(path)
        return os.path.normpath(result)

    def _normalize_separators(self, path: str) -> str:
        """Replace path separators to match the current OS.

        Args:
            path: The path to adjust.

        Returns:
            Path with OS-appropriate separators.
        """
        if self._is_windows:
            return path.replace('/', '\\')
        return path.replace('\\', '/')
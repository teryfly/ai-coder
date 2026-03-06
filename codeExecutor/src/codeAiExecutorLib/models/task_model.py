"""Complete parsed task representation with metadata and validation."""

from dataclasses import dataclass, field
from ..constants import ActionType


@dataclass
class TaskModel:
    """Represents a single parsed task with all metadata, diagnostics,
    computed properties, and validation methods.

    Attributes:
        step_line: Complete Step line text.
        action: Normalized action constant from ActionType.
        file_path: Relative file/folder path from project root.
        content: Extracted code block content.
        is_valid: Whether task passed all validation.
        error_message: Error description if invalid.
        code_block_count: Number of code blocks found in block.
        source_line_start: Starting line number in original input text.
        source_offset: Character offset in original input text.
        raw_preview: First 200 characters of raw block for diagnostics.
        unclosed_code_block: True if code block was recovered from unclosed fence.
        block_type: One of 'task', 'non_task_text', 'malformed'.
        search_replace_pairs: For PATCH_FILE: list of (search, replace) pairs.
        insert_line: For INSERT_FILE: target line number.
        destination_path: For MOVE_FILE / COPY_FILE: destination relative path.
        condition: 'if_exists' or 'if_not_exists' or None.
    """

    step_line: str = ""
    action: str = ""
    file_path: str = ""
    content: str = ""
    is_valid: bool = False
    error_message: str | None = None
    code_block_count: int = 0
    source_line_start: int = 0
    source_offset: int = 0
    raw_preview: str = ""
    unclosed_code_block: bool = False
    block_type: str = "task"
    search_replace_pairs: list[tuple[str, str]] | None = None
    insert_line: int | None = None
    destination_path: str | None = None
    condition: str | None = None

    def __post_init__(self) -> None:
        """Validate consistency of fields after initialization."""
        if self.is_valid and not self.action:
            self.is_valid = False
            self.error_message = "Missing action"
        if (
            self.is_valid
            and self.action in ActionType.REQUIRES_PATH
            and not self.file_path
        ):
            self.is_valid = False
            self.error_message = "Missing file path"

    @property
    def is_file_operation(self) -> bool:
        """True if action is a file-level operation."""
        return self.action in ActionType.FILE_ACTIONS

    @property
    def is_folder_operation(self) -> bool:
        """True if action is a folder-level operation."""
        return self.action in ActionType.FOLDER_ACTIONS

    @property
    def is_shell_command(self) -> bool:
        """True if action is a shell command execution."""
        return self.action == ActionType.EXECUTE_SHELL

    @property
    def requires_content(self) -> bool:
        """True if this action type requires code block content."""
        return self.action in ActionType.REQUIRES_CONTENT

    @property
    def requires_path(self) -> bool:
        """True if this action type requires a file path."""
        return self.action in ActionType.REQUIRES_PATH

    @property
    def is_move_or_copy(self) -> bool:
        """True if action is move or copy (requires destination)."""
        return self.action in ActionType.NEEDS_DESTINATION

    def validate_content(self) -> tuple[bool, str]:
        """Check that content is non-empty when required.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if self.requires_content and (
            not self.content or self.content.strip() == ""
        ):
            return (
                False,
                f"Action '{self.action}' requires content but none provided",
            )
        return (True, "")

    def get_summary(self) -> str:
        """Return human-readable one-line operation description."""
        content_len = len(self.content) if self.content else 0
        return (
            f"Action: {self.action} | Path: {self.file_path} "
            f"| Content: {content_len} chars | Blocks: {self.code_block_count}"
        )

    def to_dict(self) -> dict:
        """Full serialization of all fields and computed properties."""
        return {
            "step_line": self.step_line,
            "action": self.action,
            "file_path": self.file_path,
            "content": self.content,
            "is_valid": self.is_valid,
            "error_message": self.error_message,
            "code_block_count": self.code_block_count,
            "source_line_start": self.source_line_start,
            "source_offset": self.source_offset,
            "raw_preview": self.raw_preview,
            "unclosed_code_block": self.unclosed_code_block,
            "block_type": self.block_type,
            "search_replace_pairs": self.search_replace_pairs,
            "insert_line": self.insert_line,
            "destination_path": self.destination_path,
            "condition": self.condition,
            "is_file_operation": self.is_file_operation,
            "is_folder_operation": self.is_folder_operation,
            "is_shell_command": self.is_shell_command,
            "requires_content": self.requires_content,
            "requires_path": self.requires_path,
            "is_move_or_copy": self.is_move_or_copy,
        }
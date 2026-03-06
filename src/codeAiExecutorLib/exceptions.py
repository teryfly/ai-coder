"""Custom exception hierarchy for codeAiExecutorLib."""


class CodeExecutorError(Exception):
    """Base exception for all library errors."""

    def __init__(self, message: str, error_code: str = ""):
        self.message = message
        self.error_code = error_code
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class PathSecurityError(CodeExecutorError):
    """Raised when a path operation violates security constraints."""

    def __init__(self, message: str, path: str):
        self.path = path
        super().__init__(message, error_code="PATH_SECURITY_ERROR")


class CommandBlockedError(CodeExecutorError):
    """Raised when a shell command is blocked by security rules."""

    def __init__(self, message: str, command: str, reason: str):
        self.command = command
        self.reason = reason
        super().__init__(message, error_code="COMMAND_BLOCKED")


class PatchMatchError(CodeExecutorError):
    """Raised when a patch search text is not found in the target file."""

    def __init__(self, message: str, search_text: str, file_path: str):
        self.search_text = search_text
        self.file_path = file_path
        super().__init__(message, error_code="PATCH_MATCH_ERROR")
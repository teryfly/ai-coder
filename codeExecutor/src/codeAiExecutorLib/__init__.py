"""codeAiExecutorLib - AI-driven batch file, folder, and shell operations."""

from .executor import CodeExecutor
from .config import ExecutorConfig
from .constants import ActionType, StreamType

__version__ = "2.0.0"

__all__ = [
    "CodeExecutor",
    "ExecutorConfig",
    "ActionType",
    "StreamType",
]
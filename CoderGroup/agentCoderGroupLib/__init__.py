"""Top-level package exports with lazy loading.

This prevents early import of `entry.console_runner` when running
`python -m agentCoderGroupLib.entry.console_runner`.
"""

from typing import TYPE_CHECKING, Any

__all__ = [
    "OnboardServer",
    "ConsoleRunner",
    "load_config",
    "AppConfig",
    "FinalResult",
    "ProgressEvent",
    "TaskCheckpointStore",
    "ResumeCoordinator",
]

if TYPE_CHECKING:
    from .config.app_config import AppConfig
    from .entry.console_runner import ConsoleRunner
    from .entry.onboard_server import OnboardServer
    from .recovery.checkpoint_store import TaskCheckpointStore
    from .recovery.resume_coordinator import ResumeCoordinator
    from .reporting.result_models import FinalResult, ProgressEvent


def __getattr__(name: str) -> Any:
    """Lazily import public objects on first access."""
    if name == "OnboardServer":
        from .entry.onboard_server import OnboardServer

        return OnboardServer
    if name == "ConsoleRunner":
        from .entry.console_runner import ConsoleRunner

        return ConsoleRunner
    if name in {"load_config", "AppConfig"}:
        from .config.app_config import AppConfig, load_config

        return load_config if name == "load_config" else AppConfig
    if name in {"FinalResult", "ProgressEvent"}:
        from .reporting.result_models import FinalResult, ProgressEvent

        return FinalResult if name == "FinalResult" else ProgressEvent
    if name == "TaskCheckpointStore":
        from .recovery.checkpoint_store import TaskCheckpointStore

        return TaskCheckpointStore
    if name == "ResumeCoordinator":
        from .recovery.resume_coordinator import ResumeCoordinator

        return ResumeCoordinator
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
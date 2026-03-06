"""Lazy exports for entry package.

This avoids importing submodules during package import time, which prevents
runpy warnings when executing modules with `python -m`.
"""

from typing import TYPE_CHECKING, Any

__all__ = ["ConsoleRunner", "OnboardServer"]

if TYPE_CHECKING:
    # Type-check-only imports; not executed at runtime.
    from .console_runner import ConsoleRunner
    from .onboard_server import OnboardServer


def __getattr__(name: str) -> Any:
    """Lazily resolve exported symbols to avoid eager submodule imports."""
    if name == "ConsoleRunner":
        from .console_runner import ConsoleRunner

        return ConsoleRunner
    if name == "OnboardServer":
        from .onboard_server import OnboardServer

        return OnboardServer
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
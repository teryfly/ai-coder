"""Core package - execution pipeline and task routing."""

from .condition import evaluate_condition
from .pipeline import ExecutionPipeline
from .router import TaskRouter

__all__ = [
    "ExecutionPipeline",
    "TaskRouter",
    "evaluate_condition",
]
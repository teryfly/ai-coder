from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StepBlock:
    index: int
    total: int
    description: str
    action: str
    file_path: str
    destination: Optional[str]
    line_number: Optional[int]
    content: str
    raw: str


@dataclass
class ExecutionResult:
    success: bool
    summary: dict
    failed_step: Optional[StepBlock] = None
    error: Optional[str] = None


@dataclass
class ProgrammerResult:
    success: bool
    steps_completed: int
    root_dir: str
    execution_result: Optional[ExecutionResult] = None
    error_node: Optional[str] = None
    error_reason: Optional[str] = None


@dataclass
class SubTaskResult:
    phase_id: str
    success: bool
    programmer_results: list[ProgrammerResult]
    error_node: Optional[str] = None
    error_reason: Optional[str] = None


@dataclass
class FinalResult:
    task_id: str
    success: bool
    root_dir: str
    project_name: str
    sub_results: list[SubTaskResult]
    error_node: Optional[str] = None
    error_reason: Optional[str] = None
    usage_hint: Optional[str] = None


@dataclass
class ProgressEvent:
    event_type: str
    agent: str
    message: str
    data: Optional[dict] = None
    timestamp: str = ""

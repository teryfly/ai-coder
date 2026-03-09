from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _as_int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


def _as_str_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for k, v in value.items():
        if k is None or v is None:
            continue
        result[str(k)] = str(v)
    return result


@dataclass
class TaskSnapshot:
    task_id: str
    source: str
    project_id: int
    project: dict | None
    conv_name: str
    task_type: str
    requirement: str
    project_document_ids: list[int] = field(default_factory=list)
    conversation_document_ids: list[int] = field(default_factory=list)
    state: str = "running"
    current_stage: str = "architect"
    conversation_ids: dict[str, str] = field(default_factory=dict)
    architect_result: dict | None = None
    engineer_completed_phases: list[str] = field(default_factory=list)
    engineer_current_phase: str | None = None
    engineer_conv_id: str | None = None
    programmer_accumulated_output: str = ""
    programmer_step_progress: list[int] = field(default_factory=list)
    programmer_conv_id: str | None = None
    execution_completed_steps: list[int] = field(default_factory=list)
    pending_user_input: dict | None = None
    error_node: str | None = None
    error_reason: str | None = None
    created_at: str = ""
    updated_at: str = ""
    version: int = 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskSnapshot":
        payload = data if isinstance(data, dict) else {}

        return cls(
            task_id=str(payload.get("task_id", "")),
            source=str(payload.get("source", "")),
            project_id=int(payload.get("project_id", 0) or 0),
            project=payload.get("project") if isinstance(payload.get("project"), dict) else None,
            conv_name=str(payload.get("conv_name", "")),
            task_type=str(payload.get("task_type", "")),
            requirement=str(payload.get("requirement", "")),
            project_document_ids=_as_int_list(payload.get("project_document_ids")),
            conversation_document_ids=_as_int_list(payload.get("conversation_document_ids")),
            state=str(payload.get("state", "running")),
            current_stage=str(payload.get("current_stage", "architect")),
            conversation_ids=_as_str_dict(payload.get("conversation_ids")),
            architect_result=payload.get("architect_result")
            if isinstance(payload.get("architect_result"), dict)
            else None,
            engineer_completed_phases=[
                str(x) for x in (payload.get("engineer_completed_phases") or []) if x is not None
            ]
            if isinstance(payload.get("engineer_completed_phases"), list)
            else [],
            engineer_current_phase=(
                str(payload["engineer_current_phase"])
                if payload.get("engineer_current_phase") is not None
                else None
            ),
            engineer_conv_id=(
                str(payload["engineer_conv_id"])
                if payload.get("engineer_conv_id") is not None
                else None
            ),
            programmer_accumulated_output=str(payload.get("programmer_accumulated_output", "")),
            programmer_step_progress=_as_int_list(payload.get("programmer_step_progress")),
            programmer_conv_id=(
                str(payload["programmer_conv_id"])
                if payload.get("programmer_conv_id") is not None
                else None
            ),
            execution_completed_steps=_as_int_list(payload.get("execution_completed_steps")),
            pending_user_input=payload.get("pending_user_input")
            if isinstance(payload.get("pending_user_input"), dict)
            else None,
            error_node=str(payload["error_node"]) if payload.get("error_node") is not None else None,
            error_reason=(
                str(payload["error_reason"]) if payload.get("error_reason") is not None else None
            ),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            version=int(payload.get("version", 1) or 1),
        )


@dataclass
class ResumeContext:
    task_id: str
    current_stage: str
    architect_done: bool
    architect_result: dict | None
    architect_conv_id: str | None
    engineer_completed_phases: list[str]
    engineer_conv_id: str | None
    programmer_accumulated_output: str
    programmer_conv_id: str | None
    execution_completed_steps: list[int]
    pending_user_input: dict | None
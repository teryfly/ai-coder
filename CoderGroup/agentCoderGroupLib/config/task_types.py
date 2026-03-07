from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TaskType = Literal["new_dev", "formal_dev", "code_change"]

DEFAULT_TASK_TYPE: TaskType = "new_dev"

TASK_TYPE_DISPLAY: dict[TaskType, str] = {
    "new_dev": "A. 新建开发任务（Architect）",
    "formal_dev": "B. 正式开发任务（Engineer）",
    "code_change": "C. 编码任务（Programmer）",
}

TASK_TYPE_ALIASES: dict[str, TaskType] = {
    "a": "new_dev",
    "new_dev": "new_dev",
    "new-dev": "new_dev",
    "new": "new_dev",
    "architect": "new_dev",
    "b": "formal_dev",
    "formal_dev": "formal_dev",
    "formal-dev": "formal_dev",
    "formal": "formal_dev",
    "engineer": "formal_dev",
    "c": "code_change",
    "code_change": "code_change",
    "code-change": "code_change",
    "change": "code_change",
    "bugfix": "code_change",
    "programmer": "code_change",
}


@dataclass(frozen=True)
class TaskTypeOption:
    key: str
    task_type: TaskType
    title: str
    description: str


TASK_TYPE_OPTIONS: list[TaskTypeOption] = [
    TaskTypeOption(
        key="A",
        task_type="new_dev",
        title="新建开发任务",
        description="需求描述为主，由 Architect 先讨论并产出任务文档，再进入原主流程。",
    ),
    TaskTypeOption(
        key="B",
        task_type="formal_dev",
        title="正式开发任务",
        description="已有规范开发文档且项目复杂，直接进入 Engineer 分解流程。",
    ),
    TaskTypeOption(
        key="C",
        task_type="code_change",
        title="编码任务",
        description="已有项目变更/新增功能/修复缺陷，直接进入 Programmer 编码流程。",
    ),
]


def normalize_task_type(value: str | None) -> TaskType:
    if value is None:
        return DEFAULT_TASK_TYPE
    normalized = value.strip().lower()
    if not normalized:
        return DEFAULT_TASK_TYPE
    return TASK_TYPE_ALIASES.get(normalized, DEFAULT_TASK_TYPE)


def is_valid_task_type(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in TASK_TYPE_ALIASES


def get_task_type_display(task_type: TaskType) -> str:
    return TASK_TYPE_DISPLAY.get(task_type, TASK_TYPE_DISPLAY[DEFAULT_TASK_TYPE])


def get_agent_key_for_task_type(task_type: TaskType) -> str:
    if task_type == "formal_dev":
        return "engineer"
    if task_type == "code_change":
        return "programmer"
    return "architect"
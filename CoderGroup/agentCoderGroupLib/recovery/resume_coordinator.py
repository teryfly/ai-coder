from __future__ import annotations

from datetime import datetime, timezone

from .checkpoint_store import TaskCheckpointStore
from .task_snapshot import ResumeContext, TaskSnapshot


class ResumeCoordinator:
    def __init__(self, store: TaskCheckpointStore):
        self._store = store

    def create_snapshot(
        self,
        task_id: str,
        source: str,
        project_id: int,
        project: dict | None,
        conv_name: str,
        task_type: str,
        requirement: str,
        project_document_ids: list[int],
        conversation_document_ids: list[int],
    ) -> TaskSnapshot:
        stage = self._initial_stage(task_type)
        now = datetime.now(timezone.utc).isoformat()
        return TaskSnapshot(
            task_id=task_id,
            source=source,
            project_id=int(project_id),
            project=project if isinstance(project, dict) else None,
            conv_name=conv_name,
            task_type=task_type,
            requirement=requirement,
            project_document_ids=[int(x) for x in (project_document_ids or [])],
            conversation_document_ids=[int(x) for x in (conversation_document_ids or [])],
            state="running",
            current_stage=stage,
            conversation_ids={},
            architect_result=None,
            engineer_completed_phases=[],
            engineer_current_phase=None,
            engineer_conv_id=None,
            programmer_phase_conversations={},
            programmer_accumulated_output="",
            programmer_step_progress=[],
            programmer_conv_id=None,
            execution_completed_steps=[],
            pending_user_input=None,
            error_node=None,
            error_reason=None,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def build_resume_context(self, snapshot: TaskSnapshot) -> ResumeContext:
        arch_result = snapshot.architect_result if isinstance(snapshot.architect_result, dict) else None
        return ResumeContext(
            task_id=snapshot.task_id,
            current_stage=snapshot.current_stage,
            architect_done=arch_result is not None,
            architect_result=arch_result,
            architect_conv_id=snapshot.conversation_ids.get("architect"),
            engineer_completed_phases=list(snapshot.engineer_completed_phases),
            engineer_conv_id=snapshot.engineer_conv_id,
            engineer_current_phase=snapshot.engineer_current_phase,
            programmer_phase_conversations=dict(snapshot.programmer_phase_conversations) if isinstance(snapshot.programmer_phase_conversations, dict) else {},
            programmer_accumulated_output=snapshot.programmer_accumulated_output,
            programmer_conv_id=snapshot.programmer_conv_id,
            execution_completed_steps=list(snapshot.execution_completed_steps),
            pending_user_input=snapshot.pending_user_input
            if isinstance(snapshot.pending_user_input, dict)
            else None,
        )

    def get_latest_unfinished(self, source: str | None = None) -> TaskSnapshot | None:
        return self._store.get_latest_unfinished(source=source)

    def list_unfinished(self, source: str | None = None) -> list[TaskSnapshot]:
        return self._store.list_unfinished(source=source)

    @staticmethod
    def _initial_stage(task_type: str) -> str:
        if task_type == "formal_dev":
            return "engineer"
        if task_type == "code_change":
            return "programmer"
        return "architect"
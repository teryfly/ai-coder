from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..agents.programmer_agent import ProgrammerAgent
from ..reporting.progress_reporter import ProgressReporter
from ..reporting.result_models import ExecutionResult, StepBlock

if TYPE_CHECKING:
    from ..recovery.checkpoint_store import TaskCheckpointStore
    from ..recovery.task_snapshot import ResumeContext, TaskSnapshot

_SHELL_ACTIONS = {"execute shell command", "run command"}


class ExecutionPipeline:
    def __init__(self, executor: CodeExecutorAdapter, reporter: ProgressReporter):
        self._executor = executor
        self._reporter = reporter

    def run(
        self,
        code_output: str,
        root_dir: str,
        programmer: ProgrammerAgent,
        store: "TaskCheckpointStore | None" = None,
        task_id: str | None = None,
        snapshot: "TaskSnapshot | None" = None,
        resume_context: "ResumeContext | None" = None,
    ) -> ExecutionResult:
        self._reporter.emit("status", "ExecutionPipeline", "Writing all code files...")
        self._executor.write_code(root_dir, code_output)

        if store and task_id and snapshot and resume_context is None:
            snapshot.execution_completed_steps = []
            snapshot.updated_at = datetime.now(timezone.utc).isoformat()
            store.save(snapshot)

        steps = self._extract_steps(code_output)
        self._reporter.emit("status", "ExecutionPipeline", f"Parsed {len(steps)} steps to execute")

        completed_indices = set(resume_context.execution_completed_steps if resume_context else [])
        for step in steps:
            if step.index in completed_indices:
                self._reporter.emit(
                    "status", "ExecutionPipeline", f"Skipping already-completed step {step.index}"
                )
                continue

            single_dsl = self._build_single_step_dsl(step)
            if step.action.lower() in _SHELL_ACTIONS:
                ok, error = self._executor.dry_run(root_dir, single_dsl)
                if not ok:
                    self._reporter.emit(
                        "status",
                        "ExecutionPipeline",
                        f"dry_run failed for Step {step.index}/{step.total}: {error}",
                    )
                    success, repaired_step = self._repair_loop(step, error, programmer, root_dir)
                    if not success:
                        return ExecutionResult(
                            success=False,
                            summary={},
                            failed_step=repaired_step,
                            error=error,
                        )
                    step = repaired_step
                    single_dsl = self._build_single_step_dsl(step)

            self._executor.execute_full(root_dir, single_dsl)

            if store and task_id and snapshot:
                if step.index not in snapshot.execution_completed_steps:
                    snapshot.execution_completed_steps.append(step.index)
                snapshot.updated_at = datetime.now(timezone.utc).isoformat()
                store.save(snapshot)

            self._reporter.emit(
                "progress",
                "ExecutionPipeline",
                f"Step {step.index}/{step.total} completed",
            )

        return ExecutionResult(success=True, summary={"steps_executed": len(steps)})

    def _extract_steps(self, code_output: str) -> list[StepBlock]:
        blocks = re.split(r"^------", code_output, flags=re.MULTILINE)
        steps = []
        for block in blocks:
            step_m = re.search(r"Step\s*\[(\d+)/(\d+)\]\s*-\s*(.*)", block)
            action_m = re.search(r"^Action:\s*(.+)", block, re.MULTILINE)
            path_m = re.search(r"^File Path:\s*(.+)", block, re.MULTILINE)
            dest_m = re.search(r"^Destination:\s*(.+)", block, re.MULTILINE)
            line_m = re.search(r"^Line:\s*(\d+)", block, re.MULTILINE)
            code_m = re.search(r"```[\w]*\n(.*?)```", block, re.DOTALL)
            if not step_m or not action_m:
                continue
            steps.append(
                StepBlock(
                    index=int(step_m.group(1)),
                    total=int(step_m.group(2)),
                    description=step_m.group(3).strip(),
                    action=action_m.group(1).strip(),
                    file_path=path_m.group(1).strip() if path_m else "",
                    destination=dest_m.group(1).strip() if dest_m else None,
                    line_number=int(line_m.group(1)) if line_m else None,
                    content=code_m.group(1) if code_m else "",
                    raw=block.strip(),
                )
            )
        return steps

    def _build_single_step_dsl(self, step: StepBlock) -> str:
        lines = [f"Step [1/1] - {step.description}", f"Action: {step.action}"]
        if step.file_path:
            lines.append(f"File Path: {step.file_path}")
        if step.destination:
            lines.append(f"Destination: {step.destination}")
        if step.line_number is not None:
            lines.append(f"Line: {step.line_number}")
        lines.extend(["", "```bash", step.content, "```"])
        return "\n".join(lines)

    def _repair_loop(
        self,
        step: StepBlock,
        error: str,
        programmer: ProgrammerAgent,
        root_dir: str,
        max_retries: int = 5,
    ) -> tuple[bool, StepBlock]:
        step_desc = f"[{step.index}/{step.total}]"
        current_error = error
        for _ in range(max_retries):
            feedback = programmer.format_error_feedback(step_desc, current_error)
            reply = programmer.send(feedback)
            revised_steps = self._extract_steps(reply)
            target = next((s for s in revised_steps if s.action.lower() in _SHELL_ACTIONS), None)
            if not target:
                continue
            single_dsl = self._build_single_step_dsl(target)
            ok, new_error = self._executor.dry_run(root_dir, single_dsl)
            if ok:
                return True, target
            current_error = new_error
        return False, step
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Optional

from ..adapters.chat_backend_client import ChatBackendClient
from ..adapters.code_executor_adapter import CodeExecutorAdapter
from ..agents.programmer_agent import ProgrammerAgent
from ..config.app_config import AppConfig
from ..config.constants import GO_ON_PROMPT
from ..reporting.progress_reporter import ProgressReporter
from ..reporting.result_models import ExecutionResult, ProgrammerResult
from .execution_pipeline import ExecutionPipeline

if TYPE_CHECKING:
    from ..recovery.checkpoint_store import TaskCheckpointStore
    from ..recovery.task_snapshot import ResumeContext, TaskSnapshot

UserReplyProvider = Callable[[str, str], str]


def _has_incomplete_code_block(text: str) -> tuple[bool, str]:
    """
    Check if the last step has an incomplete code block.
    
    Returns:
        tuple[is_incomplete, step_number_str]
        - is_incomplete: True if last step has unpaired ```
        - step_number_str: e.g. "[3/5]" for incomplete step
    """
    lines = text.strip().split('\n')
    if not lines:
        return False, ""
    
    # Find last step marker
    step_pattern = re.compile(r'Step\s*\[(\d+)/(\d+)\]', re.IGNORECASE)
    last_step_line_idx = -1
    last_step_match = None
    
    for i, line in enumerate(lines):
        match = step_pattern.search(line)
        if match:
            last_step_line_idx = i
            last_step_match = match
    
    if last_step_line_idx == -1:
        return False, ""
    
    # Check code blocks in last step content
    last_step_content = '\n'.join(lines[last_step_line_idx:])
    code_block_count = last_step_content.count('```')
    
    is_incomplete = (code_block_count % 2) != 0
    step_str = f"[{last_step_match.group(1)}/{last_step_match.group(2)}]"
    
    return is_incomplete, step_str


class ProgrammerLoop:
    def __init__(
        self,
        client: ChatBackendClient,
        config: AppConfig,
        executor: CodeExecutorAdapter,
        reporter: ProgressReporter,
    ):
        self._client = client
        self._config = config
        self._executor = executor
        self._reporter = reporter

    def _request_user_reply(self, provider: Optional[UserReplyProvider], latest_reply: str) -> Optional[str]:
        self._reporter.emit(
            "user_input_required",
            "ProgrammerAgent",
            "Programmer reply requires user/CIO input before continuing.",
        )
        if provider is None:
            return None
        return provider("ProgrammerAgent", latest_reply).strip()

    @staticmethod
    def _checkpoint(
        store: "TaskCheckpointStore | None",
        task_id: str | None,
        snapshot: "TaskSnapshot | None",
        agent: ProgrammerAgent,
        phase_key: str | None = None,
        conv_name: str | None = None,
    ) -> None:
        if not (store and task_id and snapshot):
            return
        prog = agent.extract_step_progress(agent.accumulated_output)
        snapshot.programmer_accumulated_output = agent.accumulated_output
        snapshot.programmer_step_progress = list(prog)
        snapshot.programmer_conv_id = agent.conversation_id
        if not isinstance(snapshot.conversation_ids, dict):
            snapshot.conversation_ids = {}
        snapshot.conversation_ids["programmer"] = agent.conversation_id

        if not isinstance(snapshot.conversation_names, dict):
            snapshot.conversation_names = {}
        if conv_name:
            snapshot.conversation_names["programmer"] = conv_name

        if phase_key:
            if not isinstance(snapshot.programmer_phase_conversations, dict):
                snapshot.programmer_phase_conversations = {}
            if phase_key not in snapshot.programmer_phase_conversations:
                snapshot.programmer_phase_conversations[phase_key] = agent.conversation_id

            if not isinstance(snapshot.programmer_phase_names, dict):
                snapshot.programmer_phase_names = {}
            if conv_name and phase_key not in snapshot.programmer_phase_names:
                snapshot.programmer_phase_names[phase_key] = conv_name

        snapshot.current_stage = "programmer"
        snapshot.updated_at = datetime.now(timezone.utc).isoformat()
        store.save(snapshot)

    def _send_with_stream(
        self,
        agent: ProgrammerAgent,
        message: str,
        conversation_name: str,
        use_stream: bool = True,
    ) -> str:
        """Send message with optional streaming feedback."""
        if not use_stream:
            return agent.send(message)
        
        def on_chunk(chunk_text: str, total_lines: int, is_final: bool):
            if not is_final:
                self._reporter.emit(
                    "progress",
                    "ProgrammerAgent",
                    f"[{conversation_name}] Generating code... {total_lines} lines",
                )
        
        reply = ""
        for _chunk, _lines, _final in agent.send_stream(message, on_chunk=on_chunk):
            pass
        
        reply = agent.get_last_reply()
        final_lines = agent.get_current_line_count()
        self._reporter.emit(
            "status",
            "ProgrammerAgent",
            f"[{conversation_name}] Generated {final_lines} lines",
        )
        
        return reply

    def run(
        self,
        task_doc: str,
        project: dict,
        user_reply_provider: Optional[UserReplyProvider] = None,
        conversation_document_ids: Optional[list[int]] = None,
        conv_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        store: "TaskCheckpointStore | None" = None,
        task_id: str | None = None,
        snapshot: "TaskSnapshot | None" = None,
        resume_context: "ResumeContext | None" = None,
        phase_key: str | None = None,
        use_stream: bool = True,
    ) -> ProgrammerResult:
        root_dir = project.get("ai_work_dir", ".")
        project_id = int(project.get("id", 0) or 0)
        conversation_name = conv_name or f"programmer-{project.get('name', 'task')}"

        conv_id_to_use = None
        inject_source = False

        if phase_key and resume_context and resume_context.programmer_phase_conversations:
            conv_id_to_use = resume_context.programmer_phase_conversations.get(phase_key)

        if not conv_id_to_use and resume_context and resume_context.programmer_conv_id and resume_context.programmer_accumulated_output:
            conv_id_to_use = resume_context.programmer_conv_id
        elif not conv_id_to_use and conversation_id:
            conv_id_to_use = conversation_id

        if conv_id_to_use is None:
            inject_source = True

        agent = ProgrammerAgent(
            self._client,
            self._config,
            project_id,
            conversation_name,
            conversation_document_ids=conversation_document_ids,
            conversation_id=conv_id_to_use,
            inject_source_code=inject_source,
        )

        if resume_context and resume_context.programmer_accumulated_output:
            agent.accumulated_output = resume_context.programmer_accumulated_output

        self._checkpoint(store, task_id, snapshot, agent, phase_key, conversation_name)

        reply = ""
        if not (resume_context and resume_context.programmer_accumulated_output):
            self._reporter.emit("status", "ProgrammerAgent", f"Starting programmer loop in conversation: {conversation_name}")
            reply = self._send_with_stream(agent, task_doc, conversation_name, use_stream)
            self._reporter.emit_line_count("ProgrammerAgent", reply)
            self._checkpoint(store, task_id, snapshot, agent, phase_key, conversation_name)
        else:
            self._reporter.emit("status", "ProgrammerAgent", f"Resuming programmer loop in conversation: {conversation_name}")
            if resume_context.pending_user_input:
                reply = resume_context.pending_user_input.get("latest_reply", "")

        while not agent.is_complete(agent.get_full_code_output()):
            full_output = agent.get_full_code_output()
            
            # Check for incomplete code block
            has_incomplete, step_str = _has_incomplete_code_block(full_output)
            
            if has_incomplete:
                self._reporter.emit(
                    "status",
                    "ProgrammerAgent",
                    f"Detected incomplete code block in Step {step_str}, requesting regeneration...",
                )
                regenerate_prompt = (
                    f"The code block in Step {step_str} is incomplete (unpaired ```). "
                    f"Please regenerate Step {step_str} with complete code block, "
                    f"then continue to output all remaining steps."
                )
                reply = self._send_with_stream(agent, regenerate_prompt, conversation_name, use_stream)
                self._reporter.emit_line_count("ProgrammerAgent", reply)
                self._checkpoint(store, task_id, snapshot, agent, phase_key, conversation_name)
                continue
            
            if agent.should_auto_continue(full_output):
                continue_prompt = (
                    "If the last step's code block (```) of the last output is incomplete (``` not paired), "
                    "regenerate the incomplete step, and then continue to output the next step(s). "
                    "If the last step's code block (```) of the last output is complete (``` paired), "
                    "please continue to output all remaining steps."
                )
                reply = self._send_with_stream(agent, continue_prompt, conversation_name, use_stream)
                self._reporter.emit_line_count("ProgrammerAgent", reply)
                self._checkpoint(store, task_id, snapshot, agent, phase_key, conversation_name)
                continue

            user_message = self._request_user_reply(user_reply_provider, reply)
            if user_message is None:
                err = "Programmer requires input but no user_reply_provider is available."
                return ProgrammerResult(
                    success=False,
                    steps_completed=0,
                    root_dir=root_dir,
                    execution_result=ExecutionResult(success=False, summary={}, error=err),
                    error_node=agent.conversation_id,
                    error_reason=err,
                )

            reply = self._send_with_stream(agent, user_message or "continue", conversation_name, use_stream)
            self._reporter.emit_line_count("ProgrammerAgent", reply)
            self._checkpoint(store, task_id, snapshot, agent, phase_key, conversation_name)

        full_output = agent.get_full_code_output()
        x, _y = agent.extract_step_progress(full_output)

        pipeline = ExecutionPipeline(self._executor, self._reporter)
        exec_result = pipeline.run(
            full_output,
            root_dir,
            agent,
            store=store,
            task_id=task_id,
            snapshot=snapshot,
            resume_context=resume_context,
        )

        if not exec_result.success:
            self._reporter.emit("error", "ProgrammerAgent", f"Phase failed in conversation {conversation_name}: {exec_result.error}")
            return ProgrammerResult(
                success=False,
                steps_completed=x,
                root_dir=root_dir,
                execution_result=exec_result,
                error_node=agent.conversation_id,
                error_reason=exec_result.error,
            )

        self._reporter.emit("status", "ProgrammerAgent", f"Phase completed successfully in conversation: {conversation_name} ({x} steps)")
        return ProgrammerResult(
            success=True,
            steps_completed=x,
            root_dir=root_dir,
            execution_result=exec_result,
        )
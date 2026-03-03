"""Full execution pipeline orchestration with statistics."""

import os
import time
from typing import Generator

from ..config import ExecutorConfig
from ..infrastructure.logger import Logger
from ..infrastructure.stream_emitter import StreamEmitter
from ..parsing.block_parser import TaskBlockParser
from ..parsing.preprocessor import Preprocessor
from ..parsing.splitter import BlockSplitter
from ..security.path_guard import PathGuard
from .router import TaskRouter


class ExecutionPipeline:
    """Orchestrates the complete execution flow from input to summary.

    Handles preprocessing, block splitting, parsing, validation,
    routing, and statistics tracking. Yields stream messages for
    real-time progress feedback.
    """

    def __init__(
        self,
        config: ExecutorConfig,
        path_guard: PathGuard,
        stream: StreamEmitter,
        logger: Logger,
        router: TaskRouter,
    ) -> None:
        """Initialize execution pipeline.

        Args:
            config: Executor configuration.
            path_guard: Path security validator.
            stream: Stream message emitter.
            logger: File logger.
            router: Task router for operation dispatch.
        """
        self._config = config
        self._path_guard = path_guard
        self._stream = stream
        self._logger = logger
        self._router = router
        self.successful = 0
        self.failed = 0
        self.invalid = 0
        self.skipped = 0

    def run(
        self, content: str, dry_run: bool
    ) -> Generator[dict, None, None]:
        """Execute the full pipeline on structured input text.

        Args:
            content: Structured input text with task blocks.
            dry_run: If True, validate without executing operations.

        Yields:
            Stream message dicts for real-time progress feedback.
        """
        start_time = time.time()

        try:
            cleaned, was_modified = Preprocessor.clean(content)
            if was_modified:
                yield self._stream.info(
                    "Input preprocessed (LLM artifacts stripped)"
                )
        except Exception as e:
            yield self._stream.error(f"Preprocessing failed: {str(e)}")
            return

        try:
            blocks = BlockSplitter.split(cleaned)
            total_tasks = len(blocks)
            yield self._stream.info(f"Found {total_tasks} task(s)")
        except Exception as e:
            yield self._stream.error(f"Block splitting failed: {str(e)}")
            return

        diagnostics = BlockSplitter.detect_suspicious_separators(cleaned)
        for diag in diagnostics:
            yield self._stream.warning(diag.message)

        for idx, block in enumerate(blocks, 1):
            step_num = idx

            yield self._stream.progress(
                f"Parsing task {step_num}/{total_tasks}",
                step=step_num,
                total=total_tasks,
            )
            self._logger.info(
                f"Parsing task block {step_num}", step_num=step_num
            )

            task = TaskBlockParser.parse(block)

            if task.block_type == "non_task_text":
                self.skipped += 1
                yield self._stream.warning(
                    "Skipped non-task text block",
                    step=step_num,
                    total=total_tasks,
                    data={"raw_preview": task.raw_preview},
                )
                continue

            if not task.is_valid:
                self.invalid += 1
                diag_data = {
                    "raw_preview": task.raw_preview,
                    "source_line": task.source_line_start,
                    "source_offset": task.source_offset,
                    "block_type": task.block_type,
                    "error": task.error_message,
                }
                yield self._stream.error(
                    f"Invalid task: {task.error_message}",
                    step=step_num,
                    total=total_tasks,
                    data=diag_data,
                )
                self._logger.error(
                    f"Invalid task: {task.error_message}",
                    step_num=step_num,
                )
                continue

            yield self._stream.info(
                task.step_line, step=step_num, total=total_tasks
            )

            if task.unclosed_code_block:
                yield self._stream.warning(
                    "Code block was unclosed and recovered to end of text. "
                    "Content may be incomplete.",
                    step=step_num,
                    total=total_tasks,
                )

            if task.code_block_count > 1:
                yield self._stream.warning(
                    f"Found {task.code_block_count} code blocks, using largest",
                    step=step_num,
                    total=total_tasks,
                )

            try:
                task_failed = False
                last_result = None

                for result in self._router.dispatch(task, dry_run):
                    last_result = result

                    if result.success:
                        if result.message and not any(
                            keyword in result.message
                            for keyword in [
                                "Command completed",
                                "Changed directory",
                                "Set environment",
                                "All commands completed",
                            ]
                        ):
                            yield self._stream.shell_output(
                                result.message,
                                step=step_num,
                                total=total_tasks,
                            )
                    else:
                        yield self._stream.error(
                            f"Operation failed: {result.error or result.message}",
                            step=step_num,
                            total=total_tasks,
                            data={
                                "action": task.action,
                                "file_path": task.file_path,
                            },
                        )
                        self.failed += 1
                        self._logger.error(
                            f"Failed: {result.error or result.message}",
                            step_num=step_num,
                        )
                        task_failed = True
                        break

                if not task_failed:
                    self.successful += 1
                    lines = (
                        len(task.content.splitlines())
                        if task.content
                        else 0
                    )
                    msg = (
                        f"Task completed ({lines} lines)"
                        if lines > 0
                        else "Task completed"
                    )
                    if last_result and last_result.backup_path:
                        msg += f" (backup: {os.path.basename(last_result.backup_path)})"

                    yield self._stream.success(
                        msg, step=step_num, total=total_tasks
                    )
                    self._logger.info(msg, step_num=step_num)

            except Exception as e:
                self.failed += 1
                yield self._stream.error(
                    f"Task exception: {str(e)}",
                    step=step_num,
                    total=total_tasks,
                    data={
                        "action": task.action,
                        "file_path": task.file_path,
                        "exception_type": type(e).__name__,
                    },
                )
                self._logger.error(
                    f"Exception: {str(e)}", step_num=step_num
                )

        elapsed = time.time() - start_time
        rate = (
            (self.successful / total_tasks * 100) if total_tasks > 0 else 0
        )

        summary_data = {
            "total_tasks": total_tasks,
            "successful_tasks": self.successful,
            "failed_tasks": self.failed,
            "invalid_tasks": self.invalid,
            "skipped_tasks": self.skipped,
            "success_rate": f"{rate:.1f}%",
            "execution_time": f"{elapsed:.2f}s",
            "log_file": self._logger.log_file,
        }

        summary_msg = (
            f"Completed — success: {self.successful}, "
            f"failed: {self.failed}, invalid: {self.invalid}, "
            f"skipped: {self.skipped}"
        )

        yield self._stream.summary(summary_msg, data=summary_data)
        self._logger.info(f"Summary: {summary_msg}")
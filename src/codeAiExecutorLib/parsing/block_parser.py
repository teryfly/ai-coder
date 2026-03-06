"""Parses a single RawBlock into a TaskModel."""

from ..constants import ActionType, Patterns
from ..models.raw_block import RawBlock
from ..models.task_model import TaskModel
from .action_normalizer import ActionNormalizer
from .code_extractor import CodeBlockExtractor
from .line_cleanup import clean_structural_line
from .patch_parser import PatchParser


class TaskBlockParser:
    """Parses a RawBlock into a complete TaskModel.

    Assembles all parsing sub-modules: structure extraction,
    action normalization, code block extraction, patch parsing.

    All methods are static.
    """

    @staticmethod
    def parse(raw_block: RawBlock) -> TaskModel:
        """Parse a RawBlock into a TaskModel.

        Args:
            raw_block: The raw text block with metadata.

        Returns:
            TaskModel with all fields populated and validation status.
        """
        text = raw_block.text.replace('\r\n', '\n')
        lines = text.split('\n')

        structure = TaskBlockParser._extract_structure(lines)

        if not structure["action"]:
            block_type = TaskBlockParser._classify_block(lines)
            if block_type == "non_task_text":
                return TaskModel(
                    is_valid=False,
                    error_message="Non-task text block (likely AI commentary)",
                    block_type="non_task_text",
                    source_line_start=raw_block.line_number,
                    source_offset=raw_block.offset,
                    raw_preview=raw_block.preview,
                )
            return TaskModel(
                is_valid=False,
                error_message="Missing Action line",
                block_type="malformed",
                source_line_start=raw_block.line_number,
                source_offset=raw_block.offset,
                raw_preview=raw_block.preview,
            )

        action = ActionNormalizer.normalize(structure["action"])

        extraction = CodeBlockExtractor.extract(text)

        content = ""
        if extraction.count > 0:
            if structure["file_path"] and structure["file_path"].endswith('.md'):
                md_content = CodeBlockExtractor.extract_for_markdown(
                    text, structure["file_path_line"] or ""
                )
                if md_content is not None:
                    content = md_content
                else:
                    content = max(extraction.blocks, key=len) if extraction.count > 1 else extraction.blocks[0]
            else:
                content = max(extraction.blocks, key=len) if extraction.count > 1 else extraction.blocks[0]

        search_replace_pairs = None
        if action == ActionType.PATCH_FILE:
            pairs = PatchParser.parse(content)
            is_valid_patch, validation_msg = PatchParser.validate(pairs)
            if not is_valid_patch:
                return TaskModel(
                    is_valid=False,
                    error_message=f"Invalid patch format: {validation_msg}",
                    action=action,
                    file_path=structure["file_path"] or "",
                    content=content,
                    code_block_count=extraction.count,
                    source_line_start=raw_block.line_number,
                    source_offset=raw_block.offset,
                    raw_preview=raw_block.preview,
                    unclosed_code_block=extraction.has_unclosed,
                )
            search_replace_pairs = pairs

        if action in ActionType.REQUIRES_CONTENT and not content and not extraction.has_unclosed:
            return TaskModel(
                is_valid=False,
                error_message="Content required but not found",
                action=action,
                file_path=structure["file_path"] or "",
                code_block_count=extraction.count,
                source_line_start=raw_block.line_number,
                source_offset=raw_block.offset,
                raw_preview=raw_block.preview,
            )

        return TaskModel(
            step_line=structure["step"] or "",
            action=action,
            file_path=structure["file_path"] or "",
            content=content,
            is_valid=True,
            code_block_count=extraction.count,
            source_line_start=raw_block.line_number,
            source_offset=raw_block.offset,
            raw_preview=raw_block.preview,
            unclosed_code_block=extraction.has_unclosed,
            block_type="task",
            search_replace_pairs=search_replace_pairs,
            insert_line=structure["insert_line"],
            destination_path=structure["destination"],
            condition=structure["condition"],
        )

    @staticmethod
    def _extract_structure(lines: list[str]) -> dict:
        """Extract structural elements from block lines.

        Args:
            lines: List of lines from the block.

        Returns:
            Dict with keys: step, action, file_path, file_path_line,
            destination, condition, insert_line.
        """
        step = None
        action = None
        file_path = None
        file_path_line = None
        destination = None
        condition = None
        insert_line = None

        for line in lines:
            cleaned = clean_structural_line(line)

            if step is None and Patterns.STEP_LINE.match(cleaned):
                step = cleaned

            if action is None:
                match = Patterns.ACTION_LINE.match(cleaned)
                if match:
                    action = match.group(1).strip()

            if file_path is None:
                match = Patterns.FILE_PATH_LINE.match(cleaned)
                if match:
                    file_path = match.group(1).strip()
                    file_path_line = line

            if destination is None:
                match = Patterns.DESTINATION_LINE.match(cleaned)
                if match:
                    destination = match.group(1).strip()

            if condition is None:
                match = Patterns.CONDITION_LINE.match(cleaned)
                if match:
                    cond = match.group(1).strip().lower()
                    if cond in ("if_exists", "if_not_exists"):
                        condition = cond

            if insert_line is None:
                match = Patterns.INSERT_LINE_NUM.match(cleaned)
                if match:
                    insert_line = int(match.group(1))

        return {
            "step": step,
            "action": action,
            "file_path": file_path,
            "file_path_line": file_path_line,
            "destination": destination,
            "condition": condition,
            "insert_line": insert_line,
        }

    @staticmethod
    def _classify_block(lines: list[str]) -> str:
        """Classify a block without an action.

        Args:
            lines: List of lines from the block.

        Returns:
            'non_task_text' or 'malformed'.
        """
        structural_match_count = 0
        for line in lines:
            cleaned = clean_structural_line(line)
            if (
                Patterns.STEP_LINE.match(cleaned)
                or Patterns.ACTION_LINE.match(cleaned)
                or Patterns.FILE_PATH_LINE.match(cleaned)
            ):
                structural_match_count += 1

        if structural_match_count == 0:
            return "non_task_text"

        return "malformed"
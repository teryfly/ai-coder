import re
from dataclasses import dataclass
from typing import Optional

_ARCHITECT_END_MARKER = "End of the Coding Task Document, the estimate code file"
_ENGINEER_END_MARKER = "End of the Coding Task Document - Phase"

# Supports both "Step[1/2]" and "Step [1/2]" at line start.
_STEP_LINE_RE = re.compile(r"^\s*Step\s*\[(\d+)\s*/\s*(\d+)\]", re.IGNORECASE)


@dataclass(frozen=True)
class StepProgress:
    x: int
    y: int
    line: str


def _trim_trailing_non_digits(text: str) -> str:
    """Remove trailing non-digit characters; keep leading content unchanged."""
    return re.sub(r"\D+$", "", text.rstrip())


def _last_non_empty_line(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _ends_with_digit_after_trim(line: str) -> bool:
    trimmed = _trim_trailing_non_digits(line)
    return bool(trimmed) and trimmed[-1].isdigit()


def is_architect_completion_line(line: str) -> bool:
    """
    Architect completion condition:
    - Last line contains marker text
    - Last significant character after trimming trailing non-digits is a digit
    """
    if not line:
        return False
    if _ARCHITECT_END_MARKER not in line:
        return False
    return _ends_with_digit_after_trim(line)


def is_engineer_completion_line(line: str) -> bool:
    """
    Engineer completion condition:
    - Last line contains marker text
    - Last significant character after trimming trailing non-digits is a digit
    """
    if not line:
        return False
    if _ENGINEER_END_MARKER not in line:
        return False
    return _ends_with_digit_after_trim(line)


def parse_last_trailing_int(line: str) -> Optional[int]:
    """
    Parse trailing integer from a line after trimming non-digits at line end.
    Returns None when no trailing integer can be parsed.
    """
    trimmed = _trim_trailing_non_digits(line)
    m = re.search(r"(\d+)$", trimmed)
    if not m:
        return None
    return int(m.group(1))


def architect_is_complete(reply: str) -> bool:
    return is_architect_completion_line(_last_non_empty_line(reply))


def engineer_is_complete(reply: str) -> bool:
    return is_engineer_completion_line(_last_non_empty_line(reply))


def extract_architect_file_count(reply: str) -> int:
    line = _last_non_empty_line(reply)
    if not is_architect_completion_line(line):
        raise ValueError("Architect completion line not found in last non-empty line")
    value = parse_last_trailing_int(line)
    if value is None:
        raise ValueError("Architect trailing file count not found")
    return value


def extract_engineer_phase_and_file_count(reply: str) -> tuple[str, int]:
    line = _last_non_empty_line(reply)
    if not is_engineer_completion_line(line):
        raise ValueError("Engineer completion line not found in last non-empty line")

    phase_m = re.search(r"Phase\s*([\d.]+)", line, re.IGNORECASE)
    if not phase_m:
        raise ValueError("Engineer phase id not found in completion line")
    phase_id = phase_m.group(1)

    file_count = parse_last_trailing_int(line)
    if file_count is None:
        raise ValueError("Engineer trailing file count not found")
    return phase_id, file_count


def extract_last_step_progress(text: str) -> Optional[StepProgress]:
    """
    Find the last line that starts with Step[...] (supports 'Step[' and 'Step [').
    Return parsed progress or None if not found.
    """
    last_progress: Optional[StepProgress] = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        m = _STEP_LINE_RE.match(line)
        if not m:
            continue
        x = int(m.group(1))
        y = int(m.group(2))
        last_progress = StepProgress(x=x, y=y, line=line)
    return last_progress


def programmer_should_auto_continue(reply_or_accumulated_text: str) -> bool:
    """
    Programmer auto-continue condition:
    - Find last Step line in text
    - Continue automatically only when X < Y
    """
    progress = extract_last_step_progress(reply_or_accumulated_text)
    if progress is None:
        return False
    return progress.x < progress.y


def programmer_is_complete(reply_or_accumulated_text: str) -> bool:
    """
    Programmer completion condition for orchestration:
    - If there is a last Step line, complete when X >= Y
    - If no Step line, not complete
    """
    progress = extract_last_step_progress(reply_or_accumulated_text)
    if progress is None:
        return False
    return progress.x >= progress.y
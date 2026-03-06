import re

DEFAULT_MAX_FILES = 20
GO_ON_PROMPT = "go on"
CONTINUE_PROMPT = "continue"

ARCHITECT_TERM_RE = re.compile(
    r"End of the Coding Task Document,\s*the estimate code file:\s*(\d+)",
    re.IGNORECASE,
)

ENGINEER_TERM_RE = re.compile(
    r"End of the Coding Task Document\s*-\s*Phase\s*([\d.]+).*the estimate code file:\s*(\d+)",
    re.IGNORECASE,
)

STEP_RE = re.compile(r"Step\s*\[(\d+)/(\d+)\]", re.IGNORECASE)

"""All constant definitions and pre-compiled regex patterns."""

import re


class ActionType:
    """String constants for all supported actions."""

    CREATE_FILE = "create file"
    UPDATE_FILE = "update file"
    PATCH_FILE = "patch file"
    APPEND_FILE = "append to file"
    INSERT_FILE = "insert in file"
    DELETE_FILE = "delete file"
    MOVE_FILE = "move file"
    COPY_FILE = "copy file"
    CREATE_FOLDER = "create folder"
    DELETE_FOLDER = "delete folder"
    EXECUTE_SHELL = "execute shell command"

    ALL_ACTIONS = {
        CREATE_FILE, UPDATE_FILE, PATCH_FILE, APPEND_FILE, INSERT_FILE,
        DELETE_FILE, MOVE_FILE, COPY_FILE, CREATE_FOLDER, DELETE_FOLDER,
        EXECUTE_SHELL,
    }

    REQUIRES_CONTENT = {
        CREATE_FILE, UPDATE_FILE, PATCH_FILE, APPEND_FILE, INSERT_FILE,
        EXECUTE_SHELL,
    }

    REQUIRES_PATH = {
        CREATE_FILE, UPDATE_FILE, PATCH_FILE, APPEND_FILE, INSERT_FILE,
        DELETE_FILE, MOVE_FILE, COPY_FILE, CREATE_FOLDER, DELETE_FOLDER,
    }

    FILE_ACTIONS = {
        CREATE_FILE, UPDATE_FILE, PATCH_FILE, APPEND_FILE, INSERT_FILE,
        DELETE_FILE, MOVE_FILE, COPY_FILE,
    }

    FOLDER_ACTIONS = {CREATE_FOLDER, DELETE_FOLDER}

    NEEDS_DESTINATION = {MOVE_FILE, COPY_FILE}

    BACKUP_BEFORE = {
        UPDATE_FILE, PATCH_FILE, APPEND_FILE, INSERT_FILE, DELETE_FILE,
        MOVE_FILE,
    }


class StreamType:
    """String constants for stream message types."""

    INFO = "info"
    PROGRESS = "progress"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SHELL_OUTPUT = "shell_output"
    SUMMARY = "summary"


class Patterns:
    """Pre-compiled regex patterns used across the library."""

    SEPARATOR = re.compile(r'^\s*------\s*$', re.MULTILINE)
    SUSPICIOUS_SEPARATOR = re.compile(r'^\s*-{3,}\s*$', re.MULTILINE)
    STEP_LINE = re.compile(r'^\s*Step\b.*$', re.IGNORECASE)
    ACTION_LINE = re.compile(
        r'^\s*Action\s*[:：]\s*(.+)$', re.IGNORECASE
    )
    FILE_PATH_LINE = re.compile(
        r'^\s*(?:File\s*Path|FilePath|Path)\s*[:：]\s*(.+)$', re.IGNORECASE
    )
    DESTINATION_LINE = re.compile(
        r'^\s*(?:Destination|Dest|Target)\s*[:：]\s*(.+)$', re.IGNORECASE
    )
    CONDITION_LINE = re.compile(
        r'^\s*Condition\s*[:：]\s*(.+)$', re.IGNORECASE
    )
    INSERT_LINE_NUM = re.compile(
        r'^\s*(?:Line|Insert\s*(?:at|line))\s*[:：]\s*(\d+)$', re.IGNORECASE
    )
    SAFE_FILENAME = re.compile(r'^[\w.\-]+$')
    
    # Added re.MULTILINE to allow matching fences at start of any line
    FENCE_OPEN = re.compile(r'^(\s*`{3,})', re.MULTILINE)
    
    SEARCH_MARKER = re.compile(r'^<{4}\s*SEARCH\s*$')
    REPLACE_MARKER = re.compile(r'^={4}\s*REPLACE\s*$')
    END_MARKER = re.compile(r'^>{4}\s*$')


DANGEROUS_COMMANDS = [
    re.compile(r'\brm\b\s+-rf\s+/', re.IGNORECASE),
    re.compile(r':\s*\(\)\s*\{.*\|.*\}', re.IGNORECASE),
    re.compile(r'\bshutdown\b', re.IGNORECASE),
    re.compile(r'\breboot\b', re.IGNORECASE),
    re.compile(r'\bdrop\s+database\b', re.IGNORECASE),
    re.compile(r'\bmkfs\b', re.IGNORECASE),
    re.compile(r'\bdd\b\s+if=.+\s+of=/dev/', re.IGNORECASE),
    re.compile(r'\bchmod\b\s+-R\s+000\s+/', re.IGNORECASE),
]


LLM_THINK_PATTERNS = [
    re.compile(r'^\s*<think>[\s\S]*?</think>\s*', re.IGNORECASE),
    re.compile(r'^\s*\*Thinking.*?\*\s*', re.IGNORECASE),
    re.compile(
        r'^\s*(?:Thinking\.\.\.\s*\(\d+s elapsed\)\s*)+', re.IGNORECASE
    ),
    re.compile(
        r'^\s*[-*]?\s*(?:Thinking|Reflection|Reasoning|\u601d\u8003'
        r'|\u63a8\u7406|\u53cd\u601d)[:：].*?\n+',
        re.IGNORECASE,
    ),
    re.compile(
        r'^\s*(?:\u8ba9\u6211\u4eec\u601d\u8003\u4e00\u4e0b'
        r'|\u4ee5\u4e0b\u662f\u6211\u7684\u63a8\u7406'
        r'|\u63a8\u7406\u5982\u4e0b'
        r'|\u601d\u8003\u5982\u4e0b)[：:]?\s*\n+',
        re.IGNORECASE,
    ),
    re.compile(r'^\s*>[^\n]*\n+', re.IGNORECASE),
]


# Fixed: Match complete "[to be continued]" or "[to be continue]" markers only
# Must be at end of text, possibly with trailing whitespace
CONTINUATION_MARKER = re.compile(
    r'\s*\[to\s+be\s+continue(?:d)?\]\s*$', re.IGNORECASE
)
"""Maps raw Action values to standard ActionType constants."""

import re

from ..constants import ActionType


DIRECT_MAP: dict[str, str] = {
    "create file": ActionType.CREATE_FILE,
    "update file": ActionType.UPDATE_FILE,
    "patch file": ActionType.PATCH_FILE,
    "append to file": ActionType.APPEND_FILE,
    "insert in file": ActionType.INSERT_FILE,
    "delete file": ActionType.DELETE_FILE,
    "move file": ActionType.MOVE_FILE,
    "copy file": ActionType.COPY_FILE,
    "create folder": ActionType.CREATE_FOLDER,
    "delete folder": ActionType.DELETE_FOLDER,
    "execute shell command": ActionType.EXECUTE_SHELL,
}


ALIAS_MAP: dict[str, str] = {
    "write file": ActionType.CREATE_FILE,
    "overwrite file": ActionType.UPDATE_FILE,
    "append file": ActionType.APPEND_FILE,
    "insert file": ActionType.INSERT_FILE,
    "remove file": ActionType.DELETE_FILE,
    "rename file": ActionType.MOVE_FILE,
    "create directory": ActionType.CREATE_FOLDER,
    "mkdir": ActionType.CREATE_FOLDER,
    "delete directory": ActionType.DELETE_FOLDER,
    "rmdir": ActionType.DELETE_FOLDER,
    "remove folder": ActionType.DELETE_FOLDER,
    "execute command": ActionType.EXECUTE_SHELL,
    "run command": ActionType.EXECUTE_SHELL,
    "shell": ActionType.EXECUTE_SHELL,
    "bash": ActionType.EXECUTE_SHELL,
}


class ActionNormalizer:
    """Normalizes raw action strings to standard ActionType constants.

    Supports exact matches from the direct map and aliases from
    the alias map. Unrecognized actions are returned cleaned but
    unmapped.

    All methods are static.
    """

    @staticmethod
    def normalize(raw_action: str) -> str:
        """Normalize a raw action string to a standard ActionType constant.

        Processing:
        1. Strip, lowercase, collapse whitespace
        2. Check direct map for exact match
        3. Check alias map for exact match
        4. Return cleaned string as-is if no match

        Args:
            raw_action: Raw action string from parsed block.

        Returns:
            Normalized action string (ActionType constant or cleaned input).
        """
        cleaned = raw_action.strip().lower()
        cleaned = re.sub(r'\s+', ' ', cleaned)

        if cleaned in DIRECT_MAP:
            return DIRECT_MAP[cleaned]

        if cleaned in ALIAS_MAP:
            return ALIAS_MAP[cleaned]

        return cleaned
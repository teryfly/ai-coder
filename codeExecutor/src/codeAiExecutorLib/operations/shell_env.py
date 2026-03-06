"""Parse environment variable commands and build env dicts."""

import os
import re


def parse_env_command(cmd: str) -> tuple[bool, str, str]:
    """Parse an environment variable assignment command.

    Supports both 'export KEY=VALUE' and 'set KEY=VALUE' formats.
    The keyword (export/set) is case-insensitive.

    Args:
        cmd: Command string to parse.

    Returns:
        Tuple of (is_env_command, key, value). If not an env command,
        key and value are empty strings.
    """
    stripped = cmd.strip()
    pattern = re.compile(
        r'^\s*(?:export|set)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$',
        re.IGNORECASE,
    )
    match = pattern.match(stripped)

    if not match:
        return (False, "", "")

    key = match.group(1)
    value = match.group(2).strip()

    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1]

    return (True, key, value)


def build_env(overrides: dict) -> dict:
    """Build environment dict by merging overrides with current environment.

    Args:
        overrides: Dict of environment variable overrides.

    Returns:
        Merged environment dict.
    """
    env = os.environ.copy()
    env.update(overrides)
    return env
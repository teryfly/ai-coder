"""Shell command safety checking against dangerous patterns."""

from ..constants import DANGEROUS_COMMANDS


class CommandGuard:
    """Checks shell commands against pre-compiled dangerous patterns.

    All methods are static. The class can be instantiated for
    consistency with other handler classes but holds no state.
    """

    @staticmethod
    def check(command: str) -> tuple[bool, str]:
        """Check a single command against dangerous patterns.

        Args:
            command: The shell command string to check.

        Returns:
            Tuple of (is_safe, reason). If safe, reason is empty string.
            If unsafe, reason describes the matched pattern.
        """
        for pattern in DANGEROUS_COMMANDS:
            if pattern.search(command):
                return (
                    False,
                    f"Blocked: matches dangerous pattern: "
                    f"{pattern.pattern}",
                )
        return (True, "")

    @staticmethod
    def check_all(
        commands: list[str],
    ) -> tuple[bool, str, int]:
        """Check multiple commands, stopping at first dangerous one.

        Args:
            commands: List of shell command strings to check.

        Returns:
            Tuple of (all_safe, reason, index). If all safe, reason
            is empty and index is -1. If unsafe, reason describes the
            issue and index is the position of the dangerous command.
        """
        for index, cmd in enumerate(commands):
            is_safe, reason = CommandGuard.check(cmd)
            if not is_safe:
                return (False, reason, index)
        return (True, "", -1)
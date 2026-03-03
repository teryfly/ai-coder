"""Optional post-write content verification."""


def verify_written_content(path: str, expected: str) -> tuple[bool, str]:
    """Verify that file content matches expected content.

    Reads the file and compares to expected string. Reports
    length mismatches and content mismatches separately.

    Args:
        path: Path to file to verify.
        expected: Expected file content.

    Returns:
        Tuple of (is_valid, message). If valid, message is
        'Content verified'. If invalid, message describes the issue.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            actual = f.read()

        if actual == expected:
            return (True, "Content verified")

        if len(actual) != len(expected):
            return (
                False,
                f"Length mismatch: expected {len(expected)}, "
                f"actual {len(actual)}",
            )

        return (False, "Content mismatch")

    except Exception as e:
        return (False, f"Verification read error: {str(e)}")
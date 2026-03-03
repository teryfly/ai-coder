"""Sequential shell command execution with real-time output streaming."""

import os
import platform
import re
import shlex
import subprocess
from typing import Generator

from ..config import ExecutorConfig
from ..models.result_model import OperationResult
from ..security.command_guard import CommandGuard
from .shell_env import parse_env_command, build_env


class ShellExecutor:
    """Executes shell commands with streaming output, cd tracking, and timeout.

    Features:
    - Line-by-line real-time output streaming via generator
    - Directory change tracking across commands
    - Environment variable support (export/set)
    - Per-command timeout
    - Dangerous command blocking
    - OS-aware path normalization and command execution
    """

    def __init__(
        self, command_guard: CommandGuard, config: ExecutorConfig
    ) -> None:
        """Initialize shell executor.

        Args:
            command_guard: Guard for dangerous command detection.
            config: Executor configuration for timeout and settings.
        """
        self._command_guard = command_guard
        self._config = config
        self._is_windows = platform.system() == "Windows"

    def execute(
        self, command_block: str, cwd: str, env_vars: dict = None
    ) -> Generator[OperationResult, None, None]:
        """Execute a block of shell commands sequentially.

        Yields OperationResult for each command and output line.
        Stops on first command failure.

        Args:
            command_block: Multi-line string of commands.
            cwd: Working directory for command execution.
            env_vars: Optional environment variable overrides.

        Yields:
            OperationResult for each command execution step.
        """
        lines = [
            line.strip()
            for line in command_block.split('\n')
            if line.strip()
        ]

        commands = []
        for line in lines:
            if '&&' in line or ';' in line:
                parts = re.split(r'[;&]', line)
                commands.extend([p.strip() for p in parts if p.strip()])
            else:
                commands.append(line)

        if not commands:
            yield OperationResult(
                success=False, message="No commands to execute"
            )
            return

        is_safe, reason, idx = self._command_guard.check_all(commands)
        if not is_safe:
            yield OperationResult(
                success=False,
                message=f"Command blocked at position {idx + 1}",
                error=reason,
            )
            return

        current_dir = cwd
        current_env = build_env(env_vars or {})

        for idx, cmd in enumerate(commands, 1):
            is_env, key, value = parse_env_command(cmd)
            if is_env:
                current_env[key] = value
                yield OperationResult(
                    success=True,
                    message=f"Set environment variable: {key}={value}",
                )
                continue

            if self._is_cd_command(cmd):
                new_dir, message = self._apply_cd(cmd, current_dir)
                if new_dir != current_dir:
                    current_dir = new_dir
                    yield OperationResult(success=True, message=message)
                else:
                    yield OperationResult(success=False, message=message)
                continue

            for result in self._execute_single(
                cmd, current_dir, current_env, self._config.shell_timeout
            ):
                yield result
                if not result.success:
                    return

        yield OperationResult(success=True, message="All commands completed")

    def _is_cd_command(self, cmd: str) -> bool:
        """Check if command is a directory change command.

        Args:
            cmd: Command string to check.

        Returns:
            True if command is cd or chdir.
        """
        stripped = cmd.strip().lower()
        return (
            stripped.startswith('cd ')
            or stripped.startswith('cd\t')
            or stripped == 'cd'
            or stripped.startswith('chdir ')
        )

    def _apply_cd(
        self, cmd: str, current_dir: str
    ) -> tuple[str, str]:
        """Apply directory change command.

        Args:
            cmd: The cd command.
            current_dir: Current working directory.

        Returns:
            Tuple of (new_directory, message).
        """
        parts = cmd.strip().split(maxsplit=1)
        if len(parts) < 2:
            target = os.path.expanduser("~")
        else:
            target = parts[1].strip()
            if (target.startswith('"') and target.endswith('"')) or (
                target.startswith("'") and target.endswith("'")
            ):
                target = target[1:-1]

        if not target:
            target = os.path.expanduser("~")

        resolved = os.path.normpath(os.path.join(current_dir, target))

        if os.path.isdir(resolved):
            return (resolved, f"Changed directory to: {resolved}")
        else:
            return (current_dir, f"Directory not found: {resolved}")

    def _execute_single(
        self, cmd: str, cwd: str, env: dict, timeout: int
    ) -> Generator[OperationResult, None, None]:
        """Execute a single command with streaming output.

        Args:
            cmd: Command to execute.
            cwd: Working directory.
            env: Environment variables.
            timeout: Maximum execution time in seconds.

        Yields:
            OperationResult for each output line and final status.
        """
        if self._is_windows:
            # Special handling for mkdir on Windows
            if cmd.strip().lower().startswith('mkdir '):
                yield from self._execute_mkdir_windows(cmd, cwd, env, timeout)
                return
            
            # Special handling for echo with redirection on Windows
            if cmd.strip().lower().startswith('echo ') and '>' in cmd:
                yield from self._execute_echo_windows(cmd, cwd, env, timeout)
                return
            
            cmd_normalized = self._normalize_for_windows(cmd)
            shell_cmd = ['cmd.exe', '/c', cmd_normalized]
            shell_mode = False
        else:
            cmd_normalized = cmd
            shell_cmd = cmd_normalized
            shell_mode = True

        try:
            process = subprocess.Popen(
                shell_cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=shell_mode,
            )

            for line in process.stdout:
                line = line.rstrip('\n\r')
                if line:
                    yield OperationResult(success=True, message=line)

            process.wait(timeout=timeout)

            if process.returncode != 0:
                yield OperationResult(
                    success=False,
                    message=f"Command failed with exit code {process.returncode}: {cmd}",
                    error=f"Exit code: {process.returncode}",
                )
            else:
                yield OperationResult(
                    success=True, message=f"Command completed: {cmd}"
                )

        except subprocess.TimeoutExpired:
            process.kill()
            yield OperationResult(
                success=False,
                message=f"Command timed out after {timeout}s: {cmd}",
            )

        except FileNotFoundError:
            yield OperationResult(
                success=False, message=f"Command not found: {cmd}"
            )

        except Exception as e:
            yield OperationResult(
                success=False,
                message=f"Command error: {cmd}",
                error=str(e),
            )

    def _execute_mkdir_windows(
        self, cmd: str, cwd: str, env: dict, timeout: int
    ) -> Generator[OperationResult, None, None]:
        """Execute mkdir command on Windows with proper nested directory handling.

        Windows mkdir doesn't support -p flag, so we use Python's os.makedirs instead.

        Args:
            cmd: The mkdir command.
            cwd: Working directory.
            env: Environment variables.
            timeout: Maximum execution time in seconds.

        Yields:
            OperationResult for the operation.
        """
        # Extract path from mkdir command
        parts = cmd.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield OperationResult(
                success=False,
                message="mkdir: missing directory operand",
            )
            return
        
        path_part = parts[1].strip()
        # Remove -p flag if present
        path_part = path_part.replace('-p', '').strip()
        # Remove quotes if present
        if (path_part.startswith('"') and path_part.endswith('"')) or \
           (path_part.startswith("'") and path_part.endswith("'")):
            path_part = path_part[1:-1]
        
        # Convert forward slashes to backslashes
        path_part = path_part.replace('/', '\\')
        
        # Make it absolute if relative
        if not os.path.isabs(path_part):
            full_path = os.path.join(cwd, path_part)
        else:
            full_path = path_part
        
        # Use Python's os.makedirs to create the directory
        try:
            os.makedirs(full_path, exist_ok=True)
            yield OperationResult(
                success=True,
                message=f"Created directory: {path_part}",
            )
            yield OperationResult(
                success=True,
                message=f"Command completed: {cmd}",
            )
        except Exception as e:
            yield OperationResult(
                success=False,
                message=f"Failed to create directory: {path_part}",
                error=str(e),
            )

    def _execute_echo_windows(
        self, cmd: str, cwd: str, env: dict, timeout: int
    ) -> Generator[OperationResult, None, None]:
        """Execute echo command with file redirection on Windows.

        Uses Python's file writing instead of cmd.exe to avoid syntax issues.

        Args:
            cmd: The echo command with redirection.
            cwd: Working directory.
            env: Environment variables.
            timeout: Maximum execution time in seconds.

        Yields:
            OperationResult for the operation.
        """
        # Parse echo command: echo TEXT > FILE
        if '>' not in cmd:
            # No redirection, execute normally
            yield from self._execute_single_fallback(cmd, cwd, env, timeout)
            return
        
        # Split by > to get text and file path
        parts = cmd.split('>', 1)
        if len(parts) != 2:
            yield OperationResult(
                success=False,
                message="Invalid echo syntax",
                error=f"Command: {cmd}",
            )
            return
        
        # Extract text (remove "echo " prefix)
        text_part = parts[0].strip()
        if text_part.lower().startswith('echo '):
            text_part = text_part[5:].strip()
        
        # Remove quotes from text if present
        if (text_part.startswith('"') and text_part.endswith('"')) or \
           (text_part.startswith("'") and text_part.endswith("'")):
            text_part = text_part[1:-1]
        
        # Extract file path
        file_part = parts[1].strip()
        # Remove quotes from file path if present
        if (file_part.startswith('"') and file_part.endswith('"')) or \
           (file_part.startswith("'") and file_part.endswith("'")):
            file_part = file_part[1:-1]
        
        # Convert path separators
        file_part = file_part.replace('/', '\\')
        
        # Make it absolute if relative
        if not os.path.isabs(file_part):
            full_path = os.path.join(cwd, file_part)
        else:
            full_path = file_part
        
        # Ensure parent directory exists
        parent_dir = os.path.dirname(full_path)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                yield OperationResult(
                    success=False,
                    message=f"Failed to create parent directory: {parent_dir}",
                    error=str(e),
                )
                return
        
        # Write text to file using Python
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(text_part + '\n')
            
            yield OperationResult(
                success=True,
                message=f"Wrote text to file: {file_part}",
            )
            yield OperationResult(
                success=True,
                message=f"Command completed: {cmd}",
            )
        except Exception as e:
            yield OperationResult(
                success=False,
                message=f"Failed to write to file: {file_part}",
                error=str(e),
            )

    def _execute_single_fallback(
        self, cmd: str, cwd: str, env: dict, timeout: int
    ) -> Generator[OperationResult, None, None]:
        """Fallback execution using cmd.exe directly."""
        shell_cmd = ['cmd.exe', '/c', cmd]
        
        try:
            process = subprocess.Popen(
                shell_cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=False,
            )

            for line in process.stdout:
                line = line.rstrip('\n\r')
                if line:
                    yield OperationResult(success=True, message=line)

            process.wait(timeout=timeout)

            if process.returncode != 0:
                yield OperationResult(
                    success=False,
                    message=f"Command failed with exit code {process.returncode}: {cmd}",
                    error=f"Exit code: {process.returncode}",
                )
            else:
                yield OperationResult(
                    success=True, message=f"Command completed: {cmd}"
                )

        except Exception as e:
            yield OperationResult(
                success=False,
                message=f"Command error: {cmd}",
                error=str(e),
            )

    def _normalize_for_windows(self, cmd: str) -> str:
        """Normalize command for Windows execution.

        Converts Unix-style paths and commands to Windows equivalents.

        Args:
            cmd: Command string to normalize.

        Returns:
            Windows-compatible command string.
        """
        # Handle ls/dir commands
        if cmd.strip().startswith('ls '):
            path = cmd.strip()[3:].strip()
            if path.startswith('-'):
                # Remove Unix flags and get the path
                parts = path.split()
                actual_path = parts[-1] if parts else '.'
                actual_path = actual_path.replace('/', '\\')
                return f'dir "{actual_path}"'
            else:
                path = path.replace('/', '\\')
                return f'dir "{path}"'
        
        # Handle cat/type commands
        if cmd.strip().startswith('cat '):
            path = cmd.strip()[4:].strip()
            # Remove quotes if present
            if (path.startswith('"') and path.endswith('"')) or \
               (path.startswith("'") and path.endswith("'")):
                path = path[1:-1]
            path = path.replace('/', '\\')
            return f'type "{path}"'
        
        # Convert forward slashes to backslashes in paths
        # But avoid converting URLs
        if not any(proto in cmd for proto in ['http://', 'https://', 'ftp://']):
            # Simple heuristic: convert / to \ in what looks like paths
            pattern = re.compile(r'(?<!http:)(?<!https:)(?<!ftp:)(/[\w/.\\-]+)')
            cmd = pattern.sub(lambda m: m.group(0).replace('/', '\\'), cmd)
        
        return cmd
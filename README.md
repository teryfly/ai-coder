
# codeAIexecutorlib

AI-driven batch file, folder, and shell operations with streaming progress feedback.

## Features

- **Zero external dependencies** (Python ≥ 3.10 standard library only)
- **Streaming execution** with real-time progress feedback via Python generators
- **File operations**: create, update, patch, append, insert, delete, move, copy, read
- **Folder operations**: create, delete, list
- **Shell execution**: sequential commands with cd tracking, environment variables, timeout control
- **Security**: realpath-based path validation, dangerous command blocking, content size limits
- **Backup & rollback**: automatic backups before destructive operations with rollback support

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from codeAIexecutorlib import CodeExecutor

executor = CodeExecutor()

# Structured task input following the prompt contract
tasks = """
Step [1/2] - Create main file
Action: Create file
File Path: main.py

\`\`\`python
print("Hello, World!")
\`\`\`

------

Step [2/2] - Create output folder
Action: Create folder
File Path: output
"""

# Execute with streaming feedback
for message in executor.execute("/path/to/project", tasks):
    print(f"[{message['type']}] {message['message']}")
```

## Configuration

```python
from codeAIexecutorlib import CodeExecutor, ExecutorConfig

config = ExecutorConfig(
    backup_enabled=True,
    allow_shell=True,
    shell_timeout=300,
    verify_writes=False,
    log_level="INFO",
    log_dir="log",
    max_file_size=10_485_760,  # 10 MB
    max_path_length=260,
)

executor = CodeExecutor(config=config)
```

## Utility Methods

```python
# Read a file
content = executor.read_file("/project/root", "src/main.py")

# List directory contents
entries = executor.list_dir("/project/root", "src")
for entry in entries:
    print(f"{entry['name']} ({entry['type']}, {entry['size']} bytes)")

# Rollback a file from backup
result = executor.rollback_file("/project/root", "src/main.py")
print(result['message'])
```

## Stream Message Format

Every yielded message is a dict with:

- `message`: Human-readable description
- `type`: One of `info`, `progress`, `success`, `warning`, `error`, `shell_output`, `summary`
- `timestamp`: ISO 8601 timestamp (second precision)
- `step`: Current step number (optional)
- `total_steps`: Total number of steps (optional)
- `data`: Additional structured data (optional)

## Requirements

- Python ≥ 3.10
- No external dependencies (uses only Python standard library)

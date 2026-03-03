
# Demo Messages

This directory contains all task definitions for the interactive demo program.

## File Naming Convention

Files are named with the pattern: `{number}-{operation}-{step}.md`

- **number**: Demo number (01-13)
- **operation**: Operation name (e.g., create-file, update-file)
- **step**: Optional step identifier (e.g., create, update, patch)

## File Structure

Each file contains:

1. **Title**: Demo name and description
2. **Task Definition**: The actual task text that will be executed
3. **Optional Steps**: Multiple steps for complex demos

## Usage

These files are loaded by `main.py` using the `load_task()` function:

```python
task = load_task("01-create-file.md")
executor.execute(".", task)
```

## Customization

You can modify these files to create your own test cases:

1. Edit the file content
2. Change file paths
3. Modify code blocks
4. Add new steps

The demo program will automatically use your changes.

## Task Format

All tasks must follow the structured format:

```
Step [X/Y] - Description
Action: {action_type}
File Path: {path}
{optional parameters}

\`\`\`{language}
{content}
\`\`\`

------

{next step...}
```

## Available Actions

- Create file
- Update file
- Patch file
- Append to file
- Insert in file
- Delete file
- Move file
- Copy file
- Create folder
- Delete folder
- Execute shell command
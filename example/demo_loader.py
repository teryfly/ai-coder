"""Task loader utility for demo program."""

import os
import re


def load_task(filename: str) -> str:
    """Load task definition from demo_messages directory.
    
    Args:
        filename: Name of the task file (e.g., "01-create-file.md")
    
    Returns:
        Task definition text ready for execution.
    
    Raises:
        FileNotFoundError: If task file does not exist.
    """
    file_path = os.path.join("example", "demo_messages", filename)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Task file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Strategy: Extract everything after "## Task Definition" or "## Step" headers
    # until the end or next major section
    
    # Try pattern 1: ## Task Definition
    pattern1 = re.compile(r'##\s+Task Definition\s*\n+(.*)', re.DOTALL | re.IGNORECASE)
    match = pattern1.search(content)
    if match:
        task_content = match.group(1).strip()
        # Remove trailing markdown if any
        task_content = _clean_trailing_markdown(task_content)
        return task_content
    
    # Try pattern 2: ## Step 1: or ## Step X:
    pattern2 = re.compile(r'##\s+Step\s+\d+[:\s].*?\n+(.*)', re.DOTALL | re.IGNORECASE)
    match = pattern2.search(content)
    if match:
        task_content = match.group(1).strip()
        task_content = _clean_trailing_markdown(task_content)
        return task_content
    
    # Fallback: Look for "Step [" which is the actual task format
    pattern3 = re.compile(r'(Step\s+\[.*)', re.DOTALL)
    match = pattern3.search(content)
    if match:
        task_content = match.group(1).strip()
        task_content = _clean_trailing_markdown(task_content)
        return task_content
    
    # Last resort: return everything after first ## heading
    lines = content.split('\n')
    task_lines = []
    skip_lines = 0
    
    for i, line in enumerate(lines):
        if line.startswith('# '):
            skip_lines = i + 1
            continue
        if i >= skip_lines and line.strip():
            # Skip description paragraphs before task
            if line.startswith('Step '):
                task_lines = lines[i:]
                break
    
    if task_lines:
        result = '\n'.join(task_lines).strip()
        return _clean_trailing_markdown(result)
    
    # If nothing works, return original content
    return content.strip()


def _clean_trailing_markdown(text: str) -> str:
    """Remove trailing markdown artifacts from task text.
    
    Args:
        text: Task text that may have trailing markdown
    
    Returns:
        Cleaned text
    """
    # Don't strip anything - the problem might be here
    # Just return the text as-is
    return text


def load_task_section(filename: str, section_number: int) -> str:
    """Load specific section from a multi-step task file.
    
    Args:
        filename: Name of the task file.
        section_number: Section number to load (1-based).
    
    Returns:
        Task definition for the specified section.
    
    Raises:
        FileNotFoundError: If task file does not exist.
        ValueError: If section number is invalid.
    """
    file_path = os.path.join("example", "demo_messages", filename)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Task file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split by step headers (## Step 1:, ## Step 2:, etc.)
    step_pattern = re.compile(r'##\s+Step\s+\d+[:\s]', re.IGNORECASE)
    
    # Find all step positions
    step_positions = []
    for match in step_pattern.finditer(content):
        step_positions.append(match.end())
    
    if not step_positions:
        raise ValueError(f"No step sections found in {filename}")
    
    if section_number < 1 or section_number > len(step_positions):
        raise ValueError(
            f"Invalid section number {section_number}. "
            f"File has {len(step_positions)} sections."
        )
    
    # Extract the section content
    start_pos = step_positions[section_number - 1]
    
    if section_number < len(step_positions):
        end_pos = content.rfind('##', start_pos, step_positions[section_number])
        if end_pos == -1:
            end_pos = len(content)
    else:
        end_pos = len(content)
    
    section_content = content[start_pos:end_pos].strip()
    
    # Extract actual task (look for "Step [" format)
    task_match = re.search(r'(Step\s+\[.*)', section_content, re.DOTALL)
    if task_match:
        return task_match.group(1).strip()
    
    return section_content


def list_available_tasks() -> list[dict]:
    """List all available task files.
    
    Returns:
        List of dicts with 'number', 'name', and 'filename' keys.
    """
    demo_dir = os.path.join("example", "demo_messages")
    
    if not os.path.exists(demo_dir):
        return []
    
    tasks = []
    pattern = re.compile(r'^(\d+)-(.+)\.md$')
    
    for filename in sorted(os.listdir(demo_dir)):
        if filename == "README.md":
            continue
        
        match = pattern.match(filename)
        if match:
            number = int(match.group(1))
            name = match.group(2).replace('-', ' ').title()
            tasks.append({
                'number': number,
                'name': name,
                'filename': filename
            })
    
    return tasks


def get_task_description(filename: str) -> str:
    """Extract description from task file.
    
    Args:
        filename: Name of the task file.
    
    Returns:
        First paragraph after the title, or empty string.
    """
    file_path = os.path.join("example", "demo_messages", filename)
    
    if not os.path.exists(file_path):
        return ""
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find first paragraph after title
        lines = content.split('\n')
        description_lines = []
        found_title = False
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith('# ') and not found_title:
                found_title = True
                continue
            
            if found_title:
                if stripped and not stripped.startswith('#'):
                    description_lines.append(stripped)
                elif description_lines:
                    break
        
        return ' '.join(description_lines)
    
    except Exception:
        return ""


# Debug function to help diagnose loading issues
def debug_load_task(filename: str) -> None:
    """Print debug information about task loading.
    
    Args:
        filename: Name of the task file.
    """
    file_path = os.path.join("example", "demo_messages", filename)
    
    print(f"Loading: {file_path}")
    print(f"Exists: {os.path.exists(file_path)}")
    
    if not os.path.exists(file_path):
        return
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"\nFile length: {len(content)} characters")
    print(f"File ends with: {repr(content[-50:])}")
    print("\n" + "="*60)
    
    try:
        task = load_task(filename)
        print(f"\nExtracted task length: {len(task)} characters")
        print(f"Task ends with: {repr(task[-100:])}")
        
        # Find the code block
        import re
        fence_pattern = re.compile(r'```python\n(.*?)```', re.DOTALL)
        match = fence_pattern.search(task)
        if match:
            code = match.group(1)
            print(f"\nCode block length: {len(code)} characters")
            print(f"Code ends with: {repr(code[-100:])}")
            print(f"\nLast line of code:")
            last_line = code.strip().split('\n')[-1]
            print(f"  '{last_line}'")
            print(f"  Length: {len(last_line)}")
            print(f"  Repr: {repr(last_line)}")
    except Exception as e:
        print(f"\nError loading task: {e}")
        import traceback
        traceback.print_exc()
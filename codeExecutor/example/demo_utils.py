"""Utility functions for demo examples."""

import os
import time
from typing import Generator


def print_separator(title: str = "") -> None:
    """Print a section separator."""
    width = 80
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}\n")
    else:
        print(f"\n{'-' * width}\n")


def print_stream_messages(
    message_generator: Generator[dict, None, None],
    show_details: bool = True
) -> dict:
    """Print stream messages with formatting.
    
    Args:
        message_generator: Generator yielding stream message dicts.
        show_details: Whether to show detailed step information.
    
    Returns:
        Summary data dict if available, else empty dict.
    """
    summary_data = {}
    
    for msg in message_generator:
        msg_type = msg.get("type", "info")
        message = msg.get("message", "")
        step = msg.get("step")
        total = msg.get("total_steps")
        data = msg.get("data")
        
        # Format type indicator
        type_indicators = {
            "info": "ℹ️ ",
            "progress": "⏳",
            "success": "✅",
            "warning": "⚠️ ",
            "error": "❌",
            "shell_output": "💻",
            "summary": "📊"
        }
        indicator = type_indicators.get(msg_type, "  ")
        
        # Format step information
        step_info = ""
        if step and total and show_details:
            step_info = f"[{step}/{total}] "
        
        # Print message
        print(f"{indicator} {step_info}{message}")
        
        # Print additional data for errors and warnings
        if msg_type in ("error", "warning") and data and show_details:
            for key, value in data.items():
                if key not in ("raw_preview", "content"):
                    print(f"     {key}: {value}")
        
        # Store summary data
        if msg_type == "summary" and data:
            summary_data = data
    
    return summary_data


def wait_for_enter(prompt: str = "Press Enter to continue...") -> None:
    """Wait for user to press Enter."""
    input(f"\n{prompt}")


def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_file_content(file_path: str, max_lines: int = 20) -> None:
    """Print file content with line numbers.
    
    Args:
        file_path: Path to file to display.
        max_lines: Maximum number of lines to display.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"\n📄 File: {file_path}")
        print(f"   Lines: {len(lines)}\n")
        
        display_lines = lines[:max_lines]
        for i, line in enumerate(display_lines, 1):
            print(f"  {i:3d} | {line.rstrip()}")
        
        if len(lines) > max_lines:
            print(f"\n  ... ({len(lines) - max_lines} more lines)")
    
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except Exception as e:
        print(f"❌ Error reading file: {e}")


def print_directory_tree(root_path: str, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> None:
    """Print directory tree structure.
    
    Args:
        root_path: Root directory to display.
        prefix: Prefix for tree formatting.
        max_depth: Maximum depth to traverse.
        current_depth: Current traversal depth.
    """
    if current_depth >= max_depth:
        return
    
    try:
        entries = sorted(os.listdir(root_path))
        dirs = [e for e in entries if os.path.isdir(os.path.join(root_path, e))]
        files = [e for e in entries if os.path.isfile(os.path.join(root_path, e))]
        
        # Print directories first
        for i, dir_name in enumerate(dirs):
            is_last_dir = (i == len(dirs) - 1) and len(files) == 0
            connector = "└── " if is_last_dir else "├── "
            print(f"{prefix}{connector}📁 {dir_name}/")
            
            extension = "    " if is_last_dir else "│   "
            dir_path = os.path.join(root_path, dir_name)
            print_directory_tree(dir_path, prefix + extension, max_depth, current_depth + 1)
        
        # Print files
        for i, file_name in enumerate(files):
            is_last = i == len(files) - 1
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}📄 {file_name}")
    
    except PermissionError:
        print(f"{prefix}❌ Permission denied")
    except Exception as e:
        print(f"{prefix}❌ Error: {e}")


def confirm_action(prompt: str = "Do you want to proceed?") -> bool:
    """Ask user for confirmation.
    
    Args:
        prompt: Confirmation prompt message.
    
    Returns:
        True if user confirms, False otherwise.
    """
    response = input(f"\n{prompt} (y/n): ").strip().lower()
    return response in ('y', 'yes')
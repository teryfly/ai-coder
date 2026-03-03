"""Interactive demo program for codeAIexecutorlib.

This program demonstrates all features of the library through
an interactive menu system with real-world examples.

All task definitions are stored in example/demo_messages/ for
easy viewing and customization.
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from codefileexecutorlib import CodeExecutor
from example.demo_utils import (
    print_separator,
    print_stream_messages,
    wait_for_enter,
    clear_screen,
    print_file_content,
    print_directory_tree,
    confirm_action
)
from example.demo_loader import (
    load_task,
    load_task_section,
    get_task_description,
    debug_load_task
)

# Debug mode - set to True to see task loading details
DEBUG_MODE = False


def debug_print(message: str) -> None:
    """Print debug message if debug mode is enabled."""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")


def demo_create_file():
    """Demo: Create file operation."""
    print_separator("DEMO: Create File")
    
    print("This demo creates a new Python file with a simple function.\n")
    
    if DEBUG_MODE:
        print("\n[DEBUG MODE - Task Loading Details]")
        debug_load_task("01-create-file.md")
        print("\n" + "="*60 + "\n")
    
    task = load_task("01-create-file.md")
    
    debug_print(f"Task length: {len(task)} characters")
    debug_print(f"Task preview: {task[:200]}")
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", task))
    
    print("\n📄 Created file content:")
    print_file_content("example/output/calculator.py")
    
    wait_for_enter()


def demo_update_file():
    """Demo: Update file operation."""
    print_separator("DEMO: Update File")
    
    print("This demo updates an existing file by replacing its content.\n")
    
    # Step 1: Create initial file
    print("Step 1: Creating initial file...\n")
    create_task = load_task("02-update-file-create.md")
    
    debug_print(f"Create task length: {len(create_task)}")
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", create_task), show_details=False)
    
    print("\n📄 Initial file content:")
    print_file_content("example/output/version.txt")
    
    wait_for_enter("\nPress Enter to update the file...")
    
    # Step 2: Update the file
    print("\nStep 2: Updating file...\n")
    update_task = load_task("02-update-file-update.md")
    
    debug_print(f"Update task length: {len(update_task)}")
    
    print_stream_messages(executor.execute(".", update_task))
    
    print("\n📄 Updated file content:")
    print_file_content("example/output/version.txt")
    
    wait_for_enter()


def demo_patch_file():
    """Demo: Patch file operation."""
    print_separator("DEMO: Patch File")
    
    print("This demo applies search/replace patches to a file.\n")
    
    # Step 1: Create initial file
    print("Step 1: Creating file to patch...\n")
    create_task = load_task("03-patch-file-create.md")
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", create_task), show_details=False)
    
    print("\n📄 Original file:")
    print_file_content("example/output/app_config.py")
    
    wait_for_enter("\nPress Enter to apply patches...")
    
    # Step 2: Apply patches
    print("\nStep 2: Applying patches...\n")
    patch_task = load_task("03-patch-file-patch.md")
    
    print_stream_messages(executor.execute(".", patch_task))
    
    print("\n📄 Patched file:")
    print_file_content("example/output/app_config.py")
    
    wait_for_enter()


def demo_append_file():
    """Demo: Append to file operation."""
    print_separator("DEMO: Append to File")
    
    print("This demo appends content to an existing file.\n")
    
    # Step 1: Create initial file
    print("Step 1: Creating log file...\n")
    create_task = load_task("04-append-file-create.md")
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", create_task), show_details=False)
    
    print("\n📄 Initial log file:")
    print_file_content("example/output/app.log")
    
    wait_for_enter("\nPress Enter to append log entries...")
    
    # Step 2: Append to file
    print("\nStep 2: Appending new log entries...\n")
    append_task = load_task("04-append-file-append.md")
    
    print_stream_messages(executor.execute(".", append_task))
    
    print("\n📄 Updated log file:")
    print_file_content("example/output/app.log")
    
    wait_for_enter()


def demo_insert_file():
    """Demo: Insert in file operation."""
    print_separator("DEMO: Insert in File")
    
    print("This demo inserts content at a specific line in a file.\n")
    
    # Step 1: Create initial file
    print("Step 1: Creating Python script...\n")
    create_task = load_task("05-insert-file-create.md")
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", create_task), show_details=False)
    
    print("\n📄 Original script:")
    print_file_content("example/output/script.py")
    
    wait_for_enter("\nPress Enter to insert import statement...")
    
    # Step 2: Insert at line 3
    print("\nStep 2: Inserting import statement at line 3...\n")
    insert_task = load_task("05-insert-file-insert.md")
    
    print_stream_messages(executor.execute(".", insert_task))
    
    print("\n📄 Modified script:")
    print_file_content("example/output/script.py")
    
    wait_for_enter()


def demo_delete_file():
    """Demo: Delete file operation."""
    print_separator("DEMO: Delete File")
    
    print("This demo creates and then deletes a file.\n")
    
    # Step 1: Create file to delete
    print("Step 1: Creating temporary file...\n")
    create_task = load_task_section("06-delete-file.md", 1)
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", create_task), show_details=False)
    
    print("\n📄 File created:")
    print_file_content("example/output/temp.txt")
    
    if not confirm_action("Delete this file?"):
        print("❌ Deletion cancelled.")
        wait_for_enter()
        return
    
    # Step 2: Delete file
    print("\nStep 2: Deleting file...\n")
    delete_task = load_task_section("06-delete-file.md", 2)
    
    print_stream_messages(executor.execute(".", delete_task))
    
    # Verify deletion
    if not os.path.exists("example/output/temp.txt"):
        print("✅ File successfully deleted.")
    else:
        print("❌ File still exists.")
    
    wait_for_enter()


def demo_move_file():
    """Demo: Move file operation."""
    print_separator("DEMO: Move File")
    
    print("This demo moves a file to a different location.\n")
    
    # Step 1: Create file to move
    print("Step 1: Creating file to move...\n")
    create_task = load_task_section("07-move-file.md", 1)
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", create_task), show_details=False)
    
    print("\n📄 Original location:")
    print_file_content("example/output/document.txt")
    
    wait_for_enter("\nPress Enter to move the file...")
    
    # Step 2: Move file
    print("\nStep 2: Moving file to archive...\n")
    move_task = load_task_section("07-move-file.md", 2)
    
    print_stream_messages(executor.execute(".", move_task))
    
    print("\n📄 New location:")
    print_file_content("example/output/archive/document.txt")
    
    wait_for_enter()


def demo_copy_file():
    """Demo: Copy file operation."""
    print_separator("DEMO: Copy File")
    
    print("This demo copies a file to create a backup.\n")
    
    # Step 1: Create file to copy
    print("Step 1: Creating file to copy...\n")
    create_task = load_task_section("08-copy-file.md", 1)
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", create_task), show_details=False)
    
    print("\n📄 Source file:")
    print_file_content("example/output/important.txt")
    
    wait_for_enter("\nPress Enter to create backup...")
    
    # Step 2: Copy file
    print("\nStep 2: Creating backup copy...\n")
    copy_task = load_task_section("08-copy-file.md", 2)
    
    print_stream_messages(executor.execute(".", copy_task))
    
    print("\n📄 Backup file:")
    print_file_content("example/output/important.backup.txt")
    
    print("\n📁 Both files now exist:")
    print(f"  ✅ example/output/important.txt")
    print(f"  ✅ example/output/important.backup.txt")
    
    wait_for_enter()


def demo_create_folder():
    """Demo: Create folder operation."""
    print_separator("DEMO: Create Folder")
    
    print("This demo creates a nested directory structure.\n")
    
    task = load_task("09-create-folder.md")
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", task))
    
    print("\n📁 Created directory structure:")
    print("\nexample/output/myproject/")
    print_directory_tree("example/output/myproject", prefix="  ", max_depth=2)
    
    wait_for_enter()


def demo_delete_folder():
    """Demo: Delete folder operation."""
    print_separator("DEMO: Delete Folder")
    
    print("This demo creates and then deletes a folder.\n")
    
    # Step 1: Create folder structure
    print("Step 1: Creating folder structure...\n")
    create_task = load_task_section("10-delete-folder.md", 1)
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", create_task), show_details=False)
    
    print("\n📁 Created structure:")
    print("\nexample/output/tempdir/")
    print_directory_tree("example/output/tempdir", prefix="  ", max_depth=3)
    
    if not confirm_action("\nDelete this entire folder?"):
        print("❌ Deletion cancelled.")
        wait_for_enter()
        return
    
    # Step 2: Delete folder
    print("\nStep 2: Deleting folder...\n")
    delete_task = load_task_section("10-delete-folder.md", 2)
    
    print_stream_messages(executor.execute(".", delete_task))
    
    # Verify deletion
    if not os.path.exists("example/output/tempdir"):
        print("✅ Folder successfully deleted.")
    else:
        print("❌ Folder still exists.")
    
    wait_for_enter()


def demo_shell_command():
    """Demo: Execute shell command operation."""
    print_separator("DEMO: Execute Shell Command")
    
    print("This demo executes a series of shell commands.\n")
    print("Commands to execute:")
    print("  1. Create a directory")
    print("  2. Create a file with echo")
    print("  3. List directory contents")
    print("  4. Display file content\n")
    
    if not confirm_action("Execute these commands?"):
        print("❌ Execution cancelled.")
        wait_for_enter()
        return
    
    # Load platform-specific task
    if os.name == 'nt':  # Windows
        task = load_task("11-shell-command-windows.md")
    else:  # Unix/Linux/Mac
        task = load_task("11-shell-command-unix.md")
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", task))
    
    wait_for_enter()


def demo_batch_operations():
    """Demo: Batch operations combining multiple actions."""
    print_separator("DEMO: Batch Operations")
    
    print("This demo demonstrates a complete workflow:")
    print("  1. Create project structure")
    print("  2. Create multiple files")
    print("  3. Update configuration")
    print("  4. Create documentation\n")
    
    if not confirm_action("Execute this workflow?"):
        print("❌ Workflow cancelled.")
        wait_for_enter()
        return
    
    task = load_task("12-batch-operations.md")
    
    executor = CodeExecutor()
    summary = print_stream_messages(executor.execute(".", task))
    
    print("\n📁 Created project structure:")
    print("\nexample/output/webapp/")
    print_directory_tree("example/output/webapp", prefix="  ", max_depth=3)
    
    print("\n📊 Summary:")
    if summary:
        print(f"  Total tasks: {summary.get('total_tasks', 0)}")
        print(f"  Successful: {summary.get('successful_tasks', 0)}")
        print(f"  Failed: {summary.get('failed_tasks', 0)}")
        print(f"  Success rate: {summary.get('success_rate', '0%')}")
        print(f"  Execution time: {summary.get('execution_time', '0s')}")
    
    wait_for_enter()


def demo_utility_methods():
    """Demo: Utility methods (read_file, list_dir, rollback)."""
    print_separator("DEMO: Utility Methods")
    
    print("This demo shows utility methods provided by the library.\n")
    
    # Step 1: Create test file
    print("Step 1: Creating test file...\n")
    create_task = load_task_section("13-utility-methods.md", 1)
    
    executor = CodeExecutor()
    print_stream_messages(executor.execute(".", create_task), show_details=False)
    
    # Demo read_file
    print("\n📖 Demo: read_file() method\n")
    try:
        content = executor.read_file(".", "example/output/utility_test.txt")
        print(f"File content ({len(content)} characters):")
        print(f"---\n{content}\n---")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    wait_for_enter("\nPress Enter to continue...")
    
    # Demo list_dir
    print("\n📁 Demo: list_dir() method\n")
    try:
        entries = executor.list_dir(".", "example/output")
        print(f"Directory contents ({len(entries)} entries):\n")
        for entry in entries:
            icon = "📁" if entry['type'] == 'dir' else "📄"
            size = f"{entry['size']} bytes" if entry['type'] == 'file' else ""
            print(f"  {icon} {entry['name']:30s} {size}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    wait_for_enter("\nPress Enter to continue...")
    
    # Demo rollback
    print("\n🔄 Demo: rollback_file() method\n")
    
    # Update file to create a backup
    print("Updating file to create backup...\n")
    update_task = load_task_section("13-utility-methods.md", 2)
    print_stream_messages(executor.execute(".", update_task), show_details=False)
    
    print("\n📄 Modified content:")
    print_file_content("example/output/utility_test.txt")
    
    if confirm_action("\nRollback to original version?"):
        result = executor.rollback_file(".", "example/output/utility_test.txt")
        print(f"\n{('✅' if result.success else '❌')} {result.message}")
        
        if result.success:
            print("\n📄 Restored content:")
            print_file_content("example/output/utility_test.txt")
    
    wait_for_enter()


def show_menu():
    """Display the main menu."""
    clear_screen()
    print_separator("codeAIexecutorlib - Interactive Demo")
    
    print("Select a demo to run:\n")
    print("  File Operations:")
    print("    1. Create File")
    print("    2. Update File")
    print("    3. Patch File (Search/Replace)")
    print("    4. Append to File")
    print("    5. Insert in File")
    print("    6. Delete File")
    print("    7. Move File")
    print("    8. Copy File")
    print()
    print("  Folder Operations:")
    print("    9. Create Folder")
    print("   10. Delete Folder")
    print()
    print("  Shell Operations:")
    print("   11. Execute Shell Command")
    print()
    print("  Advanced:")
    print("   12. Batch Operations (Complete Workflow)")
    print("   13. Utility Methods (read_file, list_dir, rollback)")
    print()
    print("  Other:")
    print("   14. View Task Files (Open demo_messages directory)")
    print("   15. Toggle Debug Mode (Currently: {})".format("ON" if DEBUG_MODE else "OFF"))
    print("    0. Exit")
    print()
    print("💡 Tip: All task definitions are in example/demo_messages/")
    print("   You can edit them to customize the demos!")
    print()


def view_task_files():
    """Show information about task files."""
    print_separator("Task Files")
    
    print("Task definitions are stored in: example/demo_messages/\n")
    print("Available task files:\n")
    
    demo_dir = os.path.join("example", "demo_messages")
    if os.path.exists(demo_dir):
        files = sorted([f for f in os.listdir(demo_dir) if f.endswith('.md')])
        
        for filename in files:
            if filename == "README.md":
                continue
            
            desc = get_task_description(filename)
            print(f"  📄 {filename}")
            if desc:
                print(f"     {desc[:70]}...")
            print()
    else:
        print("  ❌ demo_messages directory not found!")
    
    print("\nYou can:")
    print("  • View these files in any text editor")
    print("  • Modify them to test your own scenarios")
    print("  • Create new task files following the same format")
    print("\nSee example/demo_messages/README.md for format details.")
    
    wait_for_enter()


def toggle_debug_mode():
    """Toggle debug mode on/off."""
    global DEBUG_MODE
    DEBUG_MODE = not DEBUG_MODE
    status = "enabled" if DEBUG_MODE else "disabled"
    print(f"\n🔧 Debug mode {status}.")
    wait_for_enter()


def main():
    """Main program loop."""
    # Ensure output directory exists
    os.makedirs("example/output", exist_ok=True)
    
    demos = {
        '1': demo_create_file,
        '2': demo_update_file,
        '3': demo_patch_file,
        '4': demo_append_file,
        '5': demo_insert_file,
        '6': demo_delete_file,
        '7': demo_move_file,
        '8': demo_copy_file,
        '9': demo_create_folder,
        '10': demo_delete_folder,
        '11': demo_shell_command,
        '12': demo_batch_operations,
        '13': demo_utility_methods,
        '14': view_task_files,
        '15': toggle_debug_mode,
    }
    
    while True:
        show_menu()
        choice = input("Enter your choice: ").strip()
        
        if choice == '0':
            print("\n👋 Thank you for using codeAIexecutorlib!")
            break
        
        if choice in demos:
            clear_screen()
            try:
                demos[choice]()
            except KeyboardInterrupt:
                print("\n\n⚠️  Demo interrupted by user.")
                wait_for_enter()
            except Exception as e:
                print(f"\n\n❌ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                wait_for_enter()
        else:
            print("\n❌ Invalid choice. Please try again.")
            wait_for_enter()


if __name__ == "__main__":
    main()
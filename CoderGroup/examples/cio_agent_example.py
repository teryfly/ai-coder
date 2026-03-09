"""
CIO-Agent Integration Example

Demonstrates three typical workflows:
- Scenario A: new_dev (Architect-driven)
- Scenario B: formal_dev (Engineer-driven)
- Scenario C: code_change (Programmer-driven)
"""

import time
from agentCoderGroupLib import load_config, OnboardServer


def progress_handler(event):
    """Handle progress events"""
    print(f"[{event.agent}] {event.message}")


def scenario_a_new_dev(server: OnboardServer):
    """
    Scenario A: New development task
    - User describes requirements verbally
    - Architect analyzes and designs
    """
    print("\n=== Scenario A: New Development (Architect-driven) ===\n")
    
    # 1. Select project
    projects = server.list_projects()
    if not projects:
        print("No projects available. Please create a project first.")
        return
    
    project = projects[0]
    project_id = project["id"]
    print(f"Selected project: {project['name']} (ID: {project_id})")
    
    # 2. Get project hierarchy (one API call)
    hierarchy = server.get_project_hierarchy(project_id)
    print(f"Existing conversations: {len(hierarchy['conversations'])}")
    print(f"Project-level references: {len(hierarchy['project_document_references'])}")
    
    # 3. Prepare context
    context = server.prepare_task_context(project_id)
    available_docs = context["available_documents"]
    print(f"Available documents: {len(available_docs)}")
    
    # 4. Select conversation-level references (demo: first 2 documents)
    conversation_doc_ids = [doc["id"] for doc in available_docs[:2]]
    print(f"Selected {len(conversation_doc_ids)} documents for conversation context")
    
    # 5. Start task with automatic conversation creation
    print("\nStarting new_dev task...")
    task_id = server.start_task_with_context(
        project_id=project_id,
        requirement="开发一个用户认证模块，支持 JWT 和密码重置功能",
        conv_name="auth-module-new-dev",
        task_type="new_dev",
        conversation_document_ids=conversation_doc_ids,
        progress_callback=progress_handler
    )
    
    print(f"Task started: {task_id}")
    
    # 6. Monitor task
    monitor_task(server, task_id)


def scenario_b_formal_dev(server: OnboardServer):
    """
    Scenario B: Formal development task
    - Specification document available
    - Complex project requiring decomposition
    """
    print("\n=== Scenario B: Formal Development (Engineer-driven) ===\n")
    
    # 1. Select project
    projects = server.list_projects()
    if not projects:
        print("No projects available. Please create a project first.")
        return
    
    project = projects[0]
    project_id = project["id"]
    
    # 2. Get project hierarchy
    hierarchy = server.get_project_hierarchy(project_id)
    
    # 3. Analyze existing conversations
    target_conv_id = None
    for conv in hierarchy["conversations"]:
        if "formal" in conv["name"].lower():
            target_conv_id = conv["id"]
            print(f"Reusing existing conversation: {conv['name']}")
            break
    
    if not target_conv_id:
        print("No suitable conversation found, will create new one")
    
    # 4. Get available documents
    context = server.prepare_task_context(project_id, target_conv_id)
    available_docs = context["available_documents"]
    
    # 5. Select references
    # Project-level: architecture, API specs
    project_doc_ids = [
        doc["id"] for doc in available_docs 
        if "架构" in doc["filename"] or "API" in doc["filename"]
    ][:2]
    
    # Conversation-level: requirement docs
    conversation_doc_ids = [
        doc["id"] for doc in available_docs 
        if "需求" in doc["filename"]
    ][:2]
    
    # Avoid duplicates
    project_refs = {ref["document_id"] for ref in hierarchy["project_document_references"]}
    conversation_doc_ids = [
        doc_id for doc_id in conversation_doc_ids 
        if doc_id not in project_refs
    ]
    
    print(f"Project-level references: {len(project_doc_ids)}")
    print(f"Conversation-level references: {len(conversation_doc_ids)}")
    
    # 6. Start formal development task
    print("\nStarting formal_dev task...")
    task_id = server.start_task_with_context(
        project_id=project_id,
        requirement="按《订单系统开发规范 v2.1》执行完整开发",
        conv_name="order-system-formal-dev",
        task_type="formal_dev",
        conversation_id=target_conv_id,
        project_document_ids=project_doc_ids,
        conversation_document_ids=conversation_doc_ids,
        progress_callback=progress_handler
    )
    
    print(f"Task started: {task_id}")
    
    # 7. Monitor task
    monitor_task(server, task_id)


def scenario_c_code_change(server: OnboardServer):
    """
    Scenario C: Code change task
    - Existing project modification
    - Bug fix or small feature addition
    """
    print("\n=== Scenario C: Code Change (Programmer-driven) ===\n")
    
    # 1. Select project
    projects = server.list_projects()
    if not projects:
        print("No projects available. Please create a project first.")
        return
    
    project = projects[0]
    project_id = project["id"]
    
    # 2. Get project hierarchy
    hierarchy = server.get_project_hierarchy(project_id)
    
    print(f"Project: {hierarchy['project_name']}")
    print(f"Existing conversations: {[c['name'] for c in hierarchy['conversations']]}")
    
    # 3. Find or create hotfix conversation
    target_conv_id = None
    for conv in hierarchy["conversations"]:
        if "hotfix" in conv["name"].lower():
            target_conv_id = conv["id"]
            print(f"Found hotfix conversation: {conv['name']}")
            break
    
    # 4. Prepare context
    context = server.prepare_task_context(project_id, target_conv_id)
    available_docs = context["available_documents"]
    
    # 5. Select references (bug report, test cases)
    conversation_doc_ids = [
        doc["id"] for doc in available_docs 
        if "bug" in doc["filename"].lower() or "测试" in doc["filename"]
    ][:2]
    
    print(f"Selected {len(conversation_doc_ids)} bug-related documents")
    
    # 6. Start code change task
    print("\nStarting code_change task...")
    task_id = server.start_task_with_context(
        project_id=project_id,
        requirement="修复订单并发扣减库存时的死锁问题，详见 bug-1234",
        conv_name="hotfix-stock-deadlock",
        task_type="code_change",
        conversation_id=target_conv_id,
        conversation_document_ids=conversation_doc_ids,
        progress_callback=progress_handler
    )
    
    print(f"Hotfix task started: {task_id}")
    
    # 7. Monitor task (faster polling for code changes)
    monitor_task(server, task_id, polling_interval=2)


def monitor_task(server: OnboardServer, task_id: str, polling_interval: int = 3):
    """
    Monitor task execution until completion or error
    
    Args:
        server: OnboardServer instance
        task_id: Task ID to monitor
        polling_interval: Polling interval in seconds
    """
    print("\n--- Task Monitoring Started ---\n")
    
    while True:
        status = server.get_status(task_id)
        
        state = status["state"]
        agent = status["current_agent"]
        message = status["message"]
        
        print(f"[{state}] {agent}: {message}")
        
        if state == "waiting_input":
            print("\n⚠️  Agent requires input")
            user_reply = input("Your reply (or press Enter for 'continue'): ").strip()
            if not user_reply:
                user_reply = "continue"
            
            server.send_user_reply(task_id, user_reply)
            print(f"Sent reply: {user_reply}\n")
        
        elif state in ("done", "error"):
            break
        
        time.sleep(polling_interval)
    
    print("\n--- Task Monitoring Ended ---\n")
    
    # Get final result
    try:
        result = server.get_result(task_id)
        if result.success:
            print("✅ Task completed successfully!")
            print(f"Root directory: {result.root_dir}")
            print(f"Project: {result.project_name}")
        else:
            print("❌ Task failed")
            print(f"Error node: {result.error_node}")
            print(f"Error reason: {result.error_reason}")
    except Exception as e:
        print(f"Failed to get result: {e}")


def demo_resume_interrupted_task(server: OnboardServer):
    """
    Demonstrate resuming interrupted tasks
    """
    print("\n=== Resuming Interrupted Tasks ===\n")
    
    # List unfinished tasks
    unfinished = server.list_unfinished_tasks(source="api")
    
    if not unfinished:
        print("No unfinished tasks found")
        return
    
    print(f"Found {len(unfinished)} unfinished task(s):")
    for i, task in enumerate(unfinished, 1):
        print(f"{i}. Task ID: {task['task_id']}")
        print(f"   Type: {task['task_type']}")
        print(f"   Stage: {task['current_stage']}")
        print(f"   State: {task['state']}")
        print(f"   Conversation: {task['conv_name']}")
        print()
    
    # Resume first task (demo)
    task_to_resume = unfinished[0]["task_id"]
    print(f"Resuming task: {task_to_resume}")
    
    server.resume_task(task_to_resume, message="继续执行")
    
    # Monitor resumed task
    monitor_task(server, task_to_resume)


def main():
    """Main entry point"""
    print("=== CIO-Agent Integration Example ===\n")
    
    # Load configuration
    config = load_config("config.yaml")
    server = OnboardServer(config)
    
    print("OnboardServer initialized successfully\n")
    
    # Menu
    print("Select a scenario to run:")
    print("  A. New Development Task (Architect-driven)")
    print("  B. Formal Development Task (Engineer-driven)")
    print("  C. Code Change Task (Programmer-driven)")
    print("  R. Resume Interrupted Task")
    print("  Q. Quit")
    
    choice = input("\nYour choice: ").strip().upper()
    
    if choice == "A":
        scenario_a_new_dev(server)
    elif choice == "B":
        scenario_b_formal_dev(server)
    elif choice == "C":
        scenario_c_code_change(server)
    elif choice == "R":
        demo_resume_interrupted_task(server)
    elif choice == "Q":
        print("Exiting...")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
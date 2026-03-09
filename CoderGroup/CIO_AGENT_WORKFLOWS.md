# CIO-Agent 调用工作流示例

## 概述

本文档提供三种典型任务类型（A/B/C）的完整调用流程示例，展示 CIO-agent 如何使用 `agentCoderGroupLib` 和 `chat_backend API` 完成端到端任务。

---

## 场景 A：新建开发任务（task_type=new_dev）

**适用场景**：用户口述需求，需要 Architect 先进行需求分析和架构设计

### 工作流程

```python
from agentCoderGroupLib import load_config, OnboardServer
import time

# 1. 初始化
config = load_config("config.yaml")
server = OnboardServer(config)

# 2. 查询项目列表，选择目标项目
projects = server.list_projects()
project_id = 42  # 假设选择了项目 42

# 3. 获取项目层级信息（一次性获取所有上下文）
hierarchy = server.get_project_hierarchy(project_id)

print(f"项目：{hierarchy['project_name']}")
print(f"现有会话数：{len(hierarchy['conversations'])}")
print(f"项目级引用文档：{len(hierarchy['project_document_references'])} 个")

# 4. 获取所有可用文档（用于选择引用）
context = server.prepare_task_context(project_id)
available_docs = context["available_documents"]

print(f"可选文档总数：{len(available_docs)}")

# 5. 选择文档引用（示例：选择前3个文档作为会话级引用）
conversation_doc_ids = [doc["id"] for doc in available_docs[:3]]

# 6. 启动新开发任务（自动创建会话）
task_id = server.start_task_with_context(
    project_id=project_id,
    requirement="开发一个用户认证模块，支持 JWT 和 OAuth2",
    conv_name="auth-module-dev",
    task_type="new_dev",
    conversation_document_ids=conversation_doc_ids,
    progress_callback=lambda event: print(f"[{event.agent}] {event.message}")
)

print(f"任务已启动：{task_id}")

# 7. 轮询任务状态
while True:
    status = server.get_status(task_id)
    print(f"[{status['state']}] {status['current_agent']}: {status['message']}")
    
    if status["state"] == "waiting_input":
        # 需要用户输入
        user_reply = input("Agent 需要反馈，请输入: ")
        server.send_user_reply(task_id, user_reply)
    elif status["state"] in ("done", "error"):
        break
    
    time.sleep(3)

# 8. 获取结果
if status["state"] == "done":
    result = server.get_result(task_id)
    print(f"任务完成！代码目录：{result.root_dir}")
else:
    print(f"任务失败：{status['message']}")
```

---

## 场景 B：正式开发任务（task_type=formal_dev）

**适用场景**：已有规范开发文档，项目复杂，需要 Engineer 进行分解

### 工作流程

```python
from agentCoderGroupLib import load_config, OnboardServer
import time

config = load_config("config.yaml")
server = OnboardServer(config)

# 1. 查询项目列表
projects = server.list_projects()
project_id = 42

# 2. 获取项目完整层级（包含会话和引用）
hierarchy = server.get_project_hierarchy(project_id)

# 3. 分析现有会话，决定是新建还是复用
existing_convs = hierarchy["conversations"]
target_conv_id = None

for conv in existing_convs:
    if conv["name"] == "formal-dev-session-1":
        target_conv_id = conv["id"]
        print(f"复用现有会话：{conv['id']}")
        break

# 4. 获取可用文档列表
context = server.prepare_task_context(project_id, target_conv_id)
available_docs = context["available_documents"]

# 5. 选择项目级和会话级引用文档
# 项目级：架构文档、API 规范
project_doc_ids = [
    doc["id"] for doc in available_docs 
    if "架构设计" in doc["filename"] or "API规范" in doc["filename"]
]

# 会话级：本次任务相关的需求文档
conversation_doc_ids = [
    doc["id"] for doc in available_docs 
    if "需求文档" in doc["filename"]
]

print(f"项目级引用：{len(project_doc_ids)} 个文档")
print(f"会话级引用：{len(conversation_doc_ids)} 个文档")

# 6. 启动正式开发任务
task_id = server.start_task_with_context(
    project_id=project_id,
    requirement="按《订单系统开发规范 v2.1》执行开发",
    conv_name="order-system-formal-dev",
    task_type="formal_dev",
    conversation_id=target_conv_id,  # 如果为 None 会自动创建
    project_document_ids=project_doc_ids,
    conversation_document_ids=conversation_doc_ids,
    progress_callback=lambda event: print(f"[{event.agent}] {event.message}")
)

print(f"任务已启动：{task_id}")

# 7. 监控任务执行（支持中断恢复）
while True:
    status = server.get_status(task_id)
    
    if status["state"] == "waiting_input":
        print(f"Agent 提问：{status['message']}")
        user_reply = input("请输入回复: ")
        server.send_user_reply(task_id, user_reply)
    elif status["state"] in ("done", "error"):
        break
    
    time.sleep(3)

# 8. 获取结果
result = server.get_result(task_id)
if result.success:
    print(f"开发完成！")
    print(f"根目录：{result.root_dir}")
    print(f"完成阶段数：{len(result.sub_results)}")
else:
    print(f"任务失败：{result.error_reason}")
```

---

## 场景 C：编码任务（task_type=code_change）

**适用场景**：既有项目变更、新增功能、修复 bug

### 工作流程

```python
from agentCoderGroupLib import load_config, OnboardServer
import time

config = load_config("config.yaml")
server = OnboardServer(config)

# 1. 查询项目列表
projects = server.list_projects()
project_id = 42

# 2. 获取项目层级信息
hierarchy = server.get_project_hierarchy(project_id)

print(f"项目：{hierarchy['project_name']}")
print(f"现有会话：{[c['name'] for c in hierarchy['conversations']]}")

# 3. 查找或创建会话
# 场景：在现有开发会话基础上修复 bug
target_conv_id = None
for conv in hierarchy["conversations"]:
    if "hotfix" in conv["name"].lower():
        target_conv_id = conv["id"]
        break

# 4. 准备任务上下文
context = server.prepare_task_context(project_id, target_conv_id)

# 5. 选择文档引用（bug 修复通常需要：现有代码文档 + bug 报告）
available_docs = context["available_documents"]
conversation_doc_ids = [
    doc["id"] for doc in available_docs 
    if "bug" in doc["filename"].lower() or "测试报告" in doc["filename"]
]

# 6. 启动编码任务（直接进入 Programmer 流程）
task_id = server.start_task_with_context(
    project_id=project_id,
    requirement="修复订单并发库存扣减时的死锁问题，详见 bug-1234.md",
    conv_name="hotfix-stock-deadlock",
    task_type="code_change",
    conversation_id=target_conv_id,
    conversation_document_ids=conversation_doc_ids,
    progress_callback=lambda event: print(f"[{event.agent}] {event.message}")
)

print(f"Hotfix 任务已启动：{task_id}")

# 7. 快速轮询（code_change 通常更快完成）
while True:
    status = server.get_status(task_id)
    
    if status["state"] == "waiting_input":
        # Programmer 提问（通常是澄清需求或确认方案）
        print(f"需要确认：{status['message']}")
        user_reply = input("请回复: ")
        server.send_user_reply(task_id, user_reply)
    elif status["state"] in ("done", "error"):
        break
    
    time.sleep(2)

# 8. 获取结果并验证
result = server.get_result(task_id)
if result.success:
    print(f"Hotfix 完成！")
    print(f"代码目录：{result.root_dir}")
    print("请运行测试验证修复效果")
else:
    print(f"修复失败：{result.error_reason}")
    print(f"错误节点：{result.error_node}")
```

---

## 典型决策流程总结

### 1. 项目选择阶段

```python
# 统一流程
projects = server.list_projects()
selected_project = projects[0]  # 或根据条件筛选
project_id = selected_project["id"]
```

### 2. 上下文分析阶段

```python
# 获取完整层级（一次 API 调用）
hierarchy = server.get_project_hierarchy(project_id)

# 分析：
# - 项目级引用文档（所有会话共享）
# - 现有会话列表（决定新建或复用）
# - 每个会话的会话级引用（评估上下文是否充分）

# 获取可选文档列表
context = server.prepare_task_context(project_id)
available_docs = context["available_documents"]
```

### 3. 文档引用决策

```python
# 原则：
# - 项目级引用：架构文档、API 规范、通用设计文档
# - 会话级引用：任务相关的需求、bug 报告、测试用例

# 示例：智能推荐
def recommend_documents(available_docs, task_type, requirement_text):
    """根据任务类型和需求文本推荐文档"""
    keywords = {
        "new_dev": ["架构", "设计模式", "编码规范"],
        "formal_dev": ["需求", "接口", "数据模型"],
        "code_change": ["bug", "测试", "现有代码"]
    }
    
    relevant = []
    for doc in available_docs:
        for keyword in keywords.get(task_type, []):
            if keyword in doc["filename"]:
                relevant.append(doc["id"])
                break
    
    return relevant

# 使用推荐
conversation_doc_ids = recommend_documents(
    available_docs, 
    task_type="formal_dev", 
    requirement_text="订单系统开发"
)
```

### 4. 会话管理决策

```python
# 决策树：
# 1. 是否有合适的现有会话？
#    - 名称匹配？
#    - 任务类型匹配？
#    - 上下文是否足够？
# 2. 如果复用：
#    - 是否需要追加会话级引用？
# 3. 如果新建：
#    - 会话命名规则（建议：任务类型-简短描述-日期）

def decide_conversation(hierarchy, task_type, requirement):
    """决定使用哪个会话"""
    for conv in hierarchy["conversations"]:
        # 检查名称、类型、引用文档是否匹配
        if is_suitable_conversation(conv, task_type, requirement):
            return conv["id"]
    
    # 没有合适的会话，返回 None 表示需要新建
    return None
```

### 5. 任务启动与监控

```python
# 统一启动接口（推荐）
task_id = server.start_task_with_context(
    project_id=project_id,
    requirement=requirement,
    conv_name=conv_name,
    task_type=task_type,
    conversation_id=conversation_id,  # None 或现有会话 ID
    project_document_ids=project_doc_ids,
    conversation_document_ids=conversation_doc_ids,
    progress_callback=progress_callback
)

# 统一监控循环
while True:
    status = server.get_status(task_id)
    
    if status["state"] == "waiting_input":
        handle_user_input(task_id, status)
    elif status["state"] in ("done", "error"):
        break
    
    time.sleep(polling_interval)
```

---

## 最佳实践

### 1. 错误处理

```python
from agentCoderGroupLib.adapters.chat_backend_client import ChatBackendError

try:
    task_id = server.start_task_with_context(...)
except ChatBackendError as e:
    print(f"Backend 错误：{e}")
    # 处理：重试、降级、通知用户
except KeyError as e:
    print(f"Task 不存在：{e}")
except ValueError as e:
    print(f"参数错误：{e}")
```

### 2. 中断恢复

```python
# 启动时检查未完成任务
unfinished = server.list_unfinished_tasks(source="api")

if unfinished:
    print(f"发现 {len(unfinished)} 个未完成任务")
    for task in unfinished:
        print(f"  - {task['task_id']}: {task['task_type']} @ {task['conv_name']}")
    
    # 用户选择恢复或放弃
    task_to_resume = unfinished[0]["task_id"]
    server.resume_task(task_to_resume, message="继续")
```

### 3. 进度回调

```python
def rich_progress_callback(event):
    """丰富的进度回调示例"""
    timestamp = event.timestamp
    agent = event.agent
    message = event.message
    
    # 根据事件类型采取不同行动
    if event.event_type == "status":
        print(f"[{timestamp}] {agent}: {message}")
    elif event.event_type == "user_input_required":
        print(f"⚠️  {agent} 需要输入")
    elif event.event_type == "complete":
        print(f"✅ 任务完成")
    elif event.event_type == "error":
        print(f"❌ 错误：{message}")
    
    # 可选：记录到日志、数据库、通知系统
    log_event_to_db(event)
```

---

## 常见问题

### Q1：如何选择合适的任务类型？

**A1：**
- `new_dev`：需求模糊、需要架构讨论 → Architect 起步
- `formal_dev`：需求明确、项目复杂（>20 文件）→ Engineer 分解
- `code_change`：既有项目小改动（<20 文件）→ Programmer 直接编码

### Q2：文档引用会自动注入吗？

**A2：** 
**不会自动注入**。必须通过以下方式之一：

1. 启动任务时传入 `project_document_ids` 和 `conversation_document_ids`
2. 使用 `start_task_with_context()` 方法自动处理
3. 手动调用 `set_project_document_references()` 和 `set_conversation_document_references()`

本库已在 Agent 发送消息时自动附带 `documents` 参数，但引用关系需 CIO-agent 预先设置。

### Q3：如何避免文档引用冲突？

**A3：**
会话级引用不能包含项目级已引用的文档，否则后端会拒绝。建议：

```python
# 获取项目级引用
project_refs = [ref["document_id"] for ref in hierarchy["project_document_references"]]

# 过滤会话级引用
conversation_doc_ids = [
    doc_id for doc_id in selected_doc_ids 
    if doc_id not in project_refs
]
```

### Q4：多个 CIO-agent 实例可以并发操作吗？

**A4：**
- 可以并发启动不同项目的任务
- 同一项目的任务建议序列化执行（避免 index 冲突）
- 使用 `list_unfinished_tasks()` 避免重复启动

---

## 进阶：自定义工作流

```python
class CIOAgentWorkflow:
    """CIO-Agent 工作流封装示例"""
    
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        self.server = OnboardServer(self.config)
    
    def smart_start_task(
        self, 
        project_id: int, 
        requirement: str,
        auto_select_docs: bool = True
    ) -> str:
        """智能启动任务：自动决策任务类型、文档引用、会话管理"""
        
        # 1. 分析需求，推断任务类型
        task_type = self._infer_task_type(requirement)
        
        # 2. 获取上下文
        hierarchy = self.server.get_project_hierarchy(project_id)
        context = self.server.prepare_task_context(project_id)
        
        # 3. 智能选择文档引用
        if auto_select_docs:
            project_docs, conv_docs = self._smart_select_docs(
                context["available_documents"],
                task_type,
                requirement
            )
        else:
            project_docs, conv_docs = [], []
        
        # 4. 决定会话策略
        conv_id = self._smart_select_conversation(hierarchy, task_type)
        
        # 5. 启动任务
        return self.server.start_task_with_context(
            project_id=project_id,
            requirement=requirement,
            conv_name=self._generate_conv_name(task_type),
            task_type=task_type,
            conversation_id=conv_id,
            project_document_ids=project_docs,
            conversation_document_ids=conv_docs
        )
    
    def _infer_task_type(self, requirement: str) -> str:
        """根据需求文本推断任务类型"""
        # 实现：关键词匹配、LLM 分析等
        pass
    
    def _smart_select_docs(self, available_docs, task_type, requirement):
        """智能选择文档引用"""
        # 实现：向量相似度、关键词匹配、LLM 推荐等
        pass
    
    def _smart_select_conversation(self, hierarchy, task_type):
        """智能选择或创建会话"""
        # 实现：名称匹配、类型匹配、时间戳等
        pass
    
    def _generate_conv_name(self, task_type: str) -> str:
        """生成会话名称"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        return f"{task_type}-{timestamp}"
```

---

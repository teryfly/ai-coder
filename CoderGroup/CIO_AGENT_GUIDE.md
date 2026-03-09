# agentCoderGroupLib — CIO-Agent 集成指南

**版本：** 0.2.0  
**更新日期：** 2026-03-09

---

## 1. 概述

`agentCoderGroupLib` 为 CIO-agent 提供异步后台任务 API，支持三类编码任务的自动化执行。本指南涵盖完整的集成流程、API 参考和典型工作流示例。

### 支持的任务类型

| 类型 | task_type | 适用场景 | 入口 Agent |
|------|-----------|----------|-----------|
| A | `new_dev` | 用户口述需求，需要架构讨论 | Architect |
| B | `formal_dev` | 已有规范文档，项目复杂 | Engineer |
| C | `code_change` | 既有项目变更、修 bug | Programmer |

### 任务状态

| 状态 | 说明 |
|------|------|
| `running` | 任务执行中 |
| `waiting_input` | 等待用户输入 |
| `interrupted` | 中断（可恢复） |
| `done` | 完成 |
| `error` | 失败 |

---

## 2. 快速开始

### 2.1 初始化

```python
from agentCoderGroupLib import load_config, OnboardServer

config = load_config("config.yaml")
server = OnboardServer(config)
```

### 2.2 简单示例（最小调用）

```python
# 1. 选择项目
projects = server.list_projects()
project_id = projects[0]["id"]

# 2. 启动任务
task_id = server.start_task(
    project_id=project_id,
    requirement="添加用户登录功能",
    conv_name="add-login-feature",
    task_type="code_change"
)

# 3. 监控任务
import time
while True:
    status = server.get_status(task_id)
    print(f"[{status['state']}] {status['message']}")
    
    if status["state"] == "waiting_input":
        server.send_user_reply(task_id, "continue")
    elif status["state"] in ("done", "error"):
        break
    
    time.sleep(3)

# 4. 获取结果
if status["state"] == "done":
    result = server.get_result(task_id)
    print(f"完成！代码目录：{result.root_dir}")
```

---

## 3. 核心概念

### 3.1 文档引用机制

**重要：文档引用不会自动注入到 LLM 上下文**

- **项目级引用**：对该项目下所有会话生效
- **会话级引用**：仅对特定会话生效，不能与项目级重复
- **注入时机**：Agent 发送消息时，本库自动查询引用并附带 `documents` 参数

CIO-agent 的职责：
1. 调用 `/v1/projects/{project_id}/hierarchy` 获取现有引用(chat_backend API)
2. 调用 `start_task()` 或 `start_task_with_context()` 时传入文档 ID
3. 或手动调用 `set_project_document_references()` / `set_conversation_document_references()`

### 3.2 会话管理策略

**新建会话 vs 复用会话**

| 场景 | 建议 |
|------|------|
| 全新任务 | 新建会话 |
| 同系列任务（如 hotfix） | 复用会话 |
| 需要不同引用文档 | 新建会话 |
| 继续未完成工作 | 复用会话（resume） |

### 3.3 任务中断与恢复

任务中断场景：
- 用户主动退出（`/exit` 命令）
- 系统崩溃
- 服务重启

恢复方法：
```python
# 查询未完成任务
unfinished = server.list_unfinished_tasks(source="api")

# 恢复任务
task_id = unfinished[0]["task_id"]
server.resume_task(task_id, message="继续执行")
```

---

## 4. API 参考

### 4.1 项目与层级查询

#### `list_projects() -> list[dict]`

获取所有项目列表（按更新时间降序）。

**返回：**
```python
[
    {
        "id": 42,
        "name": "my-project",
        "ai_work_dir": "/aiWorkDir/my-project",
        "dev_environment": "python3.11",
        ...
    }
]
```

#### `get_project_hierarchy(project_id: int) -> dict`

**一次性获取**项目完整层级信息，包含：
- 项目基础信息
- 项目级引用文档列表
- 所有会话及其会话级引用文档

**返回：**
```python
{
    "project_id": 42,
    "project_name": "my-project",
    "project_document_references": [
        {"document_id": 101, "filename": "架构设计.md", "version": 3},
        {"document_id": 102, "filename": "API规范.md", "version": 1}
    ],
    "conversations": [
        {
            "id": "uuid-1",
            "name": "feature-auth",
            "model": "GPT-5.3-Codex",
            "status": 0,
            "conversation_document_references": [
                {"document_id": 201, "filename": "认证需求.md", "version": 2}
            ]
        }
    ]
}
```

**典型用法：**
```python
# 获取层级信息用于决策
hierarchy = server.get_project_hierarchy(project_id)

# 检查是否有合适的现有会话
existing_conv = None
for conv in hierarchy["conversations"]:
    if "auth" in conv["name"].lower():
        existing_conv = conv
        break

# 检查项目级引用，避免重复
project_refs = {ref["document_id"] for ref in hierarchy["project_document_references"]}
```

#### `prepare_task_context(project_id: int, conversation_id: str | None = None) -> dict`

准备任务上下文，用于分析和决策。

**返回：**
```python
{
    "project": {...},           # 项目详情
    "hierarchy": {...},         # 完整层级
    "existing_conversation": {...} | None,  # 现有会话详情（如果提供）
    "available_documents": [...]  # 所有可用文档
}
```

### 4.2 任务启动

#### `start_task(...) -> str` （基础方法）

启动新任务（需手动管理会话和引用）。

**参数：**
```python
server.start_task(
    project_id: int,
    requirement: str,                # 需求文本
    conv_name: str,                  # 会话名称
    task_type: str = "new_dev",      # 任务类型
    project_document_ids: list[int] | None = None,      # 项目级引用
    conversation_document_ids: list[int] | None = None, # 会话级引用
    progress_callback: Callable | None = None           # 进度回调
) -> str  # 返回 task_id
```

#### `start_task_with_context(...)` → `str` （推荐）

高级启动方法，自动处理会话创建和引用设置。

**参数：**
```python
server.start_task_with_context(
    project_id: int,
    requirement: str,
    conv_name: str,
    task_type: str = "new_dev",
    conversation_id: str | None = None,  # 可选：复用现有会话
    project_document_ids: list[int] | None = None,
    conversation_document_ids: list[int] | None = None,
    progress_callback: Callable | None = None
) -> str  # 返回 task_id
```

**自动行为：**
- 如果 `conversation_id` 为 `None`，自动创建新会话
- 自动设置系统提示词（根据 `task_type`）
- 自动设置文档引用
- 如果提供 `conversation_id`，自动更新引用

**示例：**
```python
# 场景 1：新建会话
task_id = server.start_task_with_context(
    project_id=42,
    requirement="开发用户认证模块",
    conv_name="auth-module",
    task_type="new_dev",
    conversation_document_ids=[101, 102]
)

# 场景 2：复用会话
task_id = server.start_task_with_context(
    project_id=42,
    requirement="修复认证 bug",
    conv_name="auth-module",  # 会被忽略（使用现有会话名）
    task_type="code_change",
    conversation_id="existing-conv-uuid",
    conversation_document_ids=[103]  # 追加引用
)
```

#### `create_conversation_for_task(...)` → `str`

单独创建会话（用于更精细的控制）。

**参数：**
```python
server.create_conversation_for_task(
    project_id: int,
    conv_name: str,
    task_type: str,
    conversation_document_ids: list[int] | None = None
) -> str  # 返回 conversation_id
```

### 4.3 任务监控

#### `get_status(task_id: str) -> dict`

获取任务当前状态。

**返回：**
```python
{
    "task_id": "uuid",
    "state": "running" | "waiting_input" | "done" | "error",
    "current_agent": "ProgrammerAgent",
    "message": "正在执行 Step 3/10",
    "progress_events": [...]  # 最近 200 条进度事件
}
```

#### `send_user_reply(task_id: str, message: str) -> None`

发送用户回复（响应 `waiting_input` 状态）。

**示例：**
```python
status = server.get_status(task_id)
if status["state"] == "waiting_input":
    server.send_user_reply(task_id, "请继续")
```

#### `get_result(task_id: str) -> FinalResult`

获取任务结果（仅 `done` 或 `error` 状态可用）。

**返回：**
```python
FinalResult(
    task_id="uuid",
    success=True,
    root_dir="/aiWorkDir/my-project",
    project_name="my-project",
    sub_results=[...],
    error_node=None,
    error_reason=None
)
```

### 4.4 任务恢复

#### `list_unfinished_tasks(source: str = "api") -> list[dict]`

列出所有未完成任务。

**参数：**
- `source`：过滤来源（`"api"` / `"console"`）

**返回：**
```python
[
    {
        "task_id": "uuid",
        "source": "api",
        "project_id": 42,
        "conv_name": "auth-module",
        "task_type": "new_dev",
        "state": "interrupted",
        "current_stage": "programmer",
        "requirement": "开发用户认证模块...",
        "updated_at": "2026-03-09T10:00:00Z"
    }
]
```

#### `resume_task(task_id: str, message: str | None = None) -> str`

恢复中断的任务。

**参数：**
- `message`：可选，如果任务处于 `waiting_input`，直接提供回复

**返回：** 恢复后的 `task_id`（通常与传入相同）

---

## 5. 典型工作流

详细的三种任务类型工作流示例请参考 **[CIO_AGENT_WORKFLOWS.md](CIO_AGENT_WORKFLOWS.md)**。

### 5.1 标准流程（推荐）

```python
# 1. 查询项目列表
projects = server.list_projects()
project_id = select_project(projects)  # 自定义选择逻辑

# 2. 获取项目层级（一次性获取所有上下文）
hierarchy = server.get_project_hierarchy(project_id)

# 3. 准备任务上下文
context = server.prepare_task_context(project_id)

# 4. 选择文档引用
selected_docs = select_documents(
    context["available_documents"], 
    hierarchy["project_document_references"],
    task_type="formal_dev"
)

# 5. 决定会话策略
conversation_id = decide_conversation(hierarchy, task_type="formal_dev")

# 6. 启动任务
task_id = server.start_task_with_context(
    project_id=project_id,
    requirement=requirement,
    conv_name=conv_name,
    task_type=task_type,
    conversation_id=conversation_id,
    conversation_document_ids=selected_docs
)

# 7. 监控任务
while True:
    status = server.get_status(task_id)
    
    if status["state"] == "waiting_input":
        reply = get_user_input(status["message"])
        server.send_user_reply(task_id, reply)
    elif status["state"] in ("done", "error"):
        break
    
    time.sleep(3)

# 8. 获取结果
result = server.get_result(task_id)
```

### 5.2 简化流程（快速原型）

```python
# 适用于：已知项目 ID、不需要文档引用、任务简单

task_id = server.start_task(
    project_id=42,
    requirement="添加日志记录功能",
    conv_name="add-logging",
    task_type="code_change"
)

# 自动处理（阻塞直到完成）
while True:
    status = server.get_status(task_id)
    if status["state"] == "waiting_input":
        server.send_user_reply(task_id, "continue")
    elif status["state"] in ("done", "error"):
        break
    time.sleep(3)

result = server.get_result(task_id)
```

---

## 6. 文档引用最佳实践

### 6.1 引用原则

| 引用级别 | 适用文档 | 典型示例 |
|---------|---------|---------|
| 项目级 | 全局架构、通用规范 | 架构设计.md、API规范.md、编码规范.md |
| 会话级 | 任务相关、特定需求 | 需求文档.md、bug报告.md、测试用例.md |

### 6.2 避免重复引用

```python
# 获取项目级引用
hierarchy = server.get_project_hierarchy(project_id)
project_refs = {ref["document_id"] for ref in hierarchy["project_document_references"]}

# 过滤会话级引用（避免与项目级重复）
conversation_doc_ids = [
    doc_id for doc_id in selected_doc_ids 
    if doc_id not in project_refs
]

# 启动任务
server.start_task_with_context(
    ...,
    conversation_document_ids=conversation_doc_ids
)
```

### 6.3 智能文档推荐

```python
def recommend_documents(available_docs, task_type, requirement_text):
    """根据任务类型和需求推荐文档"""
    keywords = {
        "new_dev": ["架构", "设计", "模式"],
        "formal_dev": ["需求", "接口", "数据模型"],
        "code_change": ["bug", "测试", "代码"]
    }
    
    relevant = []
    for doc in available_docs:
        filename_lower = doc["filename"].lower()
        for keyword in keywords.get(task_type, []):
            if keyword in filename_lower:
                relevant.append(doc["id"])
                break
    
    return relevant
```

---

## 7. 错误处理

### 7.1 常见错误

| 错误类型 | 场景 | 处理方式 |
|---------|------|---------|
| `KeyError` | task_id 不存在 | 检查 task_id 是否正确；确认任务未被清理 |
| `ValueError` | 任务未完成调用 `get_result()` | 先检查 `state` 是否为 `done` 或 `error` |
| `ChatBackendError` | 后端 API 调用失败 | 检查网络连接、token 有效性 |

### 7.2 错误处理模板

```python
from agentCoderGroupLib.adapters.chat_backend_client import ChatBackendError

try:
    task_id = server.start_task_with_context(...)
except ChatBackendError as e:
    # 后端错误：网络、鉴权、API 异常
    logger.error(f"Backend error: {e}")
    # 重试、降级、通知
except KeyError as e:
    # Task 不存在
    logger.error(f"Task not found: {e}")
except ValueError as e:
    # 参数错误
    logger.error(f"Invalid argument: {e}")
except Exception as e:
    # 未知错误
    logger.exception(f"Unexpected error: {e}")
```

### 7.3 任务失败处理

```python
result = server.get_result(task_id)

if not result.success:
    print(f"任务失败")
    print(f"错误节点：{result.error_node}")
    print(f"错误原因：{result.error_reason}")
    
    # 根据错误类型采取行动
    if "timeout" in result.error_reason.lower():
        # 重试
        pass
    elif "validation" in result.error_reason.lower():
        # 修正参数后重试
        pass
    else:
        # 通知管理员
        pass
```

---

## 8. 进度监控

### 8.1 进度回调

```python
def progress_callback(event):
    """
    event: ProgressEvent
        - event_type: str (status/progress/user_input_required/complete/error)
        - agent: str (ArchitectAgent/EngineerAgent/ProgrammerAgent/...)
        - message: str
        - timestamp: str (ISO 8601)
        - data: dict | None
    """
    print(f"[{event.timestamp}] [{event.agent}] {event.message}")
    
    # 可选：记录到日志、数据库、发送通知
    if event.event_type == "error":
        send_alert(f"任务失败：{event.message}")

# 启动任务时注册
task_id = server.start_task_with_context(
    ...,
    progress_callback=progress_callback
)
```

### 8.2 轮询状态

```python
import time

while True:
    status = server.get_status(task_id)
    
    # 显示进度
    print(f"[{status['state']}] {status['current_agent']}: {status['message']}")
    
    # 处理用户输入
    if status["state"] == "waiting_input":
        reply = input("请输入: ")
        server.send_user_reply(task_id, reply)
    
    # 终止条件
    elif status["state"] in ("done", "error"):
        break
    
    time.sleep(3)  # 轮询间隔
```

---

## 9. 高级用法

### 9.1 批量任务管理

```python
class TaskManager:
    def __init__(self, server: OnboardServer):
        self.server = server
        self.tasks = {}
    
    def start_batch(self, project_id: int, requirements: list[str]):
        """批量启动任务"""
        for i, req in enumerate(requirements):
            task_id = self.server.start_task(
                project_id=project_id,
                requirement=req,
                conv_name=f"batch-task-{i}",
                task_type="code_change"
            )
            self.tasks[task_id] = {"requirement": req, "status": "running"}
    
    def monitor_all(self):
        """监控所有任务"""
        while True:
            all_done = True
            for task_id in self.tasks:
                status = self.server.get_status(task_id)
                self.tasks[task_id]["status"] = status["state"]
                
                if status["state"] not in ("done", "error"):
                    all_done = False
            
            if all_done:
                break
            
            time.sleep(5)
```

### 9.2 自定义工作流封装

详见 **[CIO_AGENT_WORKFLOWS.md](CIO_AGENT_WORKFLOWS.md)** 的"进阶：自定义工作流"章节。

---

## 10. 常见问题（FAQ）

### Q1：如何选择合适的任务类型？

**A：**
- 需求模糊、需要讨论 → `new_dev` (Architect)
- 需求明确、复杂（>20 文件）→ `formal_dev` (Engineer)
- 既有项目小改动（<20 文件）→ `code_change` (Programmer)

### Q2：文档引用会自动注入吗？

**A：** 
**不会**。必须通过以下方式之一：
1. `start_task()` 时传入 `project_document_ids` 和 `conversation_document_ids`
2. 使用 `start_task_with_context()`（推荐）
3. 手动调用 `set_project_document_references()` / `set_conversation_document_references()`

本库已在 Agent 发送消息时自动附带 `documents` 参数，但引用关系需 CIO-agent 预先设置。

### Q3：如何避免文档引用冲突？

**A：**
会话级引用不能包含项目级已引用的文档。建议：

```python
hierarchy = server.get_project_hierarchy(project_id)
project_refs = {ref["document_id"] for ref in hierarchy["project_document_references"]}

conversation_doc_ids = [
    doc_id for doc_id in selected_doc_ids 
    if doc_id not in project_refs
]
```

### Q4：多个 CIO-agent 实例可以并发操作吗？

**A：**
- ✅ 可以并发启动不同项目的任务
- ⚠️ 同一项目的任务建议序列化（避免 checkpoint 冲突）
- ✅ 使用 `list_unfinished_tasks()` 避免重复启动

### Q5：如何处理长时间运行的任务？

**A：**
- 使用异步架构（CIO-agent 启动任务后继续处理其他请求）
- 通过 `progress_callback` 接收实时进度
- 定时轮询 `get_status()`
- 利用中断恢复机制

### Q6：任务中断后如何恢复？

**A：**
```python
# 查询未完成任务
unfinished = server.list_unfinished_tasks(source="api")

# 选择要恢复的任务
task_id = unfinished[0]["task_id"]

# 恢复任务
server.resume_task(task_id, message="继续执行")

# 继续监控
while True:
    status = server.get_status(task_id)
    # ...
```

---

## 11. 完整示例

详见 **[CIO_AGENT_WORKFLOWS.md](CIO_AGENT_WORKFLOWS.md)**，包含：

- 场景 A：新建开发任务（task_type=new_dev）
- 场景 B：正式开发任务（task_type=formal_dev）
- 场景 C：编码任务（task_type=code_change）

每个场景包含完整的代码示例和决策流程。

---

## 12. 参考资源

- **安装部署**：[INSTALL.md](INSTALL.md)
- **工作流示例**：[CIO_AGENT_WORKFLOWS.md](CIO_AGENT_WORKFLOWS.md)
- **chat_backend API**：项目根目录下的 API 文档
- **源码**：`agentCoderGroupLib/` 目录

---

## 13. 更新日志

**v0.2.0 (2026-03-09)**
- 新增 `get_project_hierarchy()` 方法
- 新增 `prepare_task_context()` 方法
- 新增 `start_task_with_context()` 高级启动方法
- 新增 `create_conversation_for_task()` 会话创建方法
- 新增完整工作流示例文档（CIO_AGENT_WORKFLOWS.md）
- 更新文档引用说明

**v0.1.0 (2026-03-08)**
- 初始版本
- 基础任务启动和监控功能

# agentCoderGroupLib — CIO-Agent 调用说明文档

## 1. 概述

`agentCoderGroupLib` 通过 `OnboardServer` 类向 CIO-agent 提供一套**后台任务型 API**。每个编码任务在独立线程中异步执行，CIO-agent 通过轮询或回调获取进度，并可在需要时注入用户确认消息。

### 核心工作流

```
CIO-agent
  │
  ├─ start_task(project_id, requirement, conv_name)
  │     └─ 返回 task_id（立即返回，后台开始执行）
  │
  ├─ get_status(task_id)  [轮询]
  │     └─ state: "running" | "waiting_input" | "done" | "error"
  │
  ├─ send_user_reply(task_id, message)  [仅 waiting_input 时]
  │
  └─ get_result(task_id)  [state == "done" 时]
        └─ 返回 FinalResult
```

---

## 2. 初始化

```python
from agentCoderGroupLib import load_config, OnboardServer

# 从项目根目录加载配置（或传入绝对路径）
config = load_config("config.yaml")

# 创建服务实例（单例，可全局共享）
server = OnboardServer(config)
```

---

## 3. API 参考

---

### 3.1 `start_task` — 启动编码任务

```python
task_id: str = server.start_task(
    project_id: int,      # chat_backend 中的项目 ID
    requirement: str,     # 编码需求描述（自然语言）
    conv_name: str,       # 新建 Architect 会话的名称
)
```

**行为说明：**
- 立即返回 `task_id`（UUID 字符串），后台线程启动
- 自动从 chat_backend 拉取 `category_id=5` 的知识库文档，注入 Architect 首条消息
- 自动根据 Architect 估算的文件数路由至 Programmer 或 Engineer

**示例：**

```python
task_id = server.start_task(
    project_id=42,
    requirement="实现一个 FastAPI 用户认证模块，包含注册、登录、JWT 刷新接口",
    conv_name="auth-module-2025-03-06",
)
print(f"Task started: {task_id}")
```

---

### 3.2 `get_status` — 查询任务状态

```python
status: dict = server.get_status(task_id: str)
```

**返回结构：**

```python
{
    "task_id": "uuid-string",
    "state": "running",           # running | waiting_input | done | error
    "current_agent": "ProgrammerAgent",
    "message": "Step 3/7 completed",
    "progress_events": [          # 最近 200 条事件（环形缓冲）
        {
            "event_type": "progress",   # status | output | error | complete | user_input_required
            "agent": "ProgrammerAgent",
            "message": "Step 3/7 completed",
            "timestamp": "2025-03-06T10:00:00+00:00",
            "data": None
        },
        ...
    ]
}
```

**state 枚举说明：**

| state | 说明 |
|-------|------|
| `running` | 任务正在执行，可继续轮询 |
| `waiting_input` | Agent 提出了问题，需调用 `send_user_reply` 才能继续 |
| `done` | 任务成功完成，可调用 `get_result` |
| `error` | 任务执行出错，`message` 字段含错误原因 |

**推荐轮询间隔：** 2–5 秒

**示例：**

```python
import time

while True:
    status = server.get_status(task_id)
    print(f"[{status['state']}] {status['message']}")

    if status["state"] == "waiting_input":
        # 转发给人工或上层决策系统
        user_reply = ask_human_or_policy(status["message"])
        server.send_user_reply(task_id, user_reply)

    elif status["state"] in ("done", "error"):
        break

    time.sleep(3)
```

---

### 3.3 `send_user_reply` — 注入用户回复

```python
server.send_user_reply(task_id: str, message: str)
```

**何时调用：** 仅当 `get_status` 返回 `state == "waiting_input"` 时。

**触发条件：** Agent 回复中包含以下任一特征：
- 最后 3 行含 `?`
- 含 `[Awaiting confirmation]`
- 含 `please confirm`（不区分大小写）
- 含 `do you want`（不区分大小写）

**示例：**

```python
server.send_user_reply(task_id, "yes, proceed with PostgreSQL as the database")
```

---

### 3.4 `get_result` — 获取最终结果

```python
result: FinalResult = server.get_result(task_id: str)
```

**返回 `FinalResult` 结构：**

```python
@dataclass
class FinalResult:
    task_id: str                    # 与 start_task 返回的 task_id 相同
    success: bool                   # 整体是否成功
    root_dir: str                   # 代码写入的根目录（来自 project.ai_work_dir）
    project_name: str               # 项目名称
    sub_results: list[SubTaskResult]  # Engineer 分解的各子阶段结果（小任务为空列表）
    error_node: str | None          # 失败时的 conversation_id
    error_reason: str | None        # 失败原因描述
    usage_hint: str | None          # 使用说明（如有）
```

**`SubTaskResult` 结构：**

```python
@dataclass
class SubTaskResult:
    phase_id: str                     # 例如 "1.1", "1.2"
    success: bool
    programmer_results: list[ProgrammerResult]
    error_node: str | None
    error_reason: str | None
```

**示例：**

```python
result = server.get_result(task_id)

if result.success:
    print(f"代码已写入: {result.root_dir}")
    print(f"项目: {result.project_name}")
    for sub in result.sub_results:
        steps = sum(pr.steps_completed for pr in sub.programmer_results)
        print(f"  Phase {sub.phase_id}: {steps} 步完成")
else:
    print(f"执行失败")
    print(f"  失败节点: conversation/{result.error_node}")
    print(f"  失败原因: {result.error_reason}")
```

---

### 3.5 `list_projects` — 列出项目

```python
projects: list[dict] = server.list_projects()
```

返回 chat_backend 中所有项目，按 `updated_time` 降序排列。每个项目包含：

| 字段 | 说明 |
|------|------|
| `id` | 项目 ID（传给 `start_task` 的 `project_id`） |
| `name` | 项目名称 |
| `ai_work_dir` | 代码工作目录（代码将写入此路径） |
| `updated_time` | 最近更新时间 |

---

### 3.6 `list_tasks` — 列出所有任务

```python
tasks: list[dict] = server.list_tasks()
```

返回当前进程内所有任务的摘要：

```python
[
    {
        "task_id": "uuid",
        "state": "done",
        "current_agent": "ExecutionPipeline",
        "message": "Step 7/7 completed"
    },
    ...
]
```

---

## 4. 完整集成示例

```python
import time
from agentCoderGroupLib import load_config, OnboardServer
from agentCoderGroupLib import FinalResult

def run_coding_task(
    project_id: int,
    requirement: str,
    conv_name: str,
    config_path: str = "config.yaml",
    poll_interval: float = 3.0,
) -> FinalResult:
    """
    完整的一次性编码任务调用，返回 FinalResult。
    waiting_input 状态时自动回复"continue"（可按需替换为人工审批逻辑）。
    """
    config = load_config(config_path)
    server = OnboardServer(config)

    task_id = server.start_task(project_id, requirement, conv_name)
    print(f"[started] task_id={task_id}")

    while True:
        status = server.get_status(task_id)
        state = status["state"]
        print(f"[{state}] {status['current_agent']}: {status['message']}")

        if state == "waiting_input":
            # --- 替换此处为你的审批逻辑 ---
            server.send_user_reply(task_id, "continue")

        elif state == "done":
            return server.get_result(task_id)

        elif state == "error":
            result = FinalResult(
                task_id=task_id,
                success=False,
                root_dir="",
                project_name="",
                sub_results=[],
                error_reason=status["message"],
            )
            return result

        time.sleep(poll_interval)


# --- 调用示例 ---
if __name__ == "__main__":
    result = run_coding_task(
        project_id=42,
        requirement="为现有 Flask 应用添加 Redis 缓存层，缓存所有 GET 接口响应 60 秒",
        conv_name="redis-cache-2025-03-06",
    )

    if result.success:
        print(f"\n=== 完成 ===")
        print(f"代码路径: {result.root_dir}")
    else:
        print(f"\n=== 失败 ===")
        print(f"原因: {result.error_reason}")
        print(f"会话: conversation/{result.error_node}")
```

---

## 5. 并发多任务

`OnboardServer` 是线程安全的，支持同时启动多个任务：

```python
config = load_config()
server = OnboardServer(config)

# 同时启动 3 个任务
task_ids = [
    server.start_task(42, "实现用户模块", "user-module"),
    server.start_task(42, "实现订单模块", "order-module"),
    server.start_task(42, "实现支付模块", "payment-module"),
]

# 轮询所有任务
while task_ids:
    for tid in list(task_ids):
        s = server.get_status(tid)
        if s["state"] in ("done", "error"):
            task_ids.remove(tid)
            print(f"Task {tid}: {s['state']}")
    time.sleep(3)
```

> **注意**：每个任务会向 chat_backend 创建独立的会话（Architect / Engineer / Programmer 各一个），并发任务数受 chat_backend 并发限制约束。

---

## 6. ProgressEvent 事件类型参考

`progress_events` 列表中每条事件的 `event_type` 含义：

| event_type | 触发场景 |
|------------|---------|
| `status` | Agent 状态变化（启动、路由、阶段切换） |
| `output` | Agent 收到回复（含行数统计） |
| `progress` | 单步执行完成（Step X/Y completed） |
| `error` | 执行出错（dry_run 失败、修复失败等） |
| `complete` | 任务整体完成 |
| `user_input_required` | Agent 需要人工确认（会触发 waiting_input 状态） |

---

## 7. 错误处理

| 场景 | 处理方式 |
|------|---------|
| `get_status` 抛 `KeyError` | `task_id` 不存在，检查是否由同一 `server` 实例启动 |
| `get_result` 抛 `ValueError` | 任务尚未完成，等待 `state == "done"` 后再调用 |
| `state == "error"` | 读取 `status["message"]` 获取错误原因；如需重试，重新调用 `start_task` |
| Shell 命令 dry_run 失败 | 内部自动最多重试 5 次并要求 Programmer 修复；全部失败后 `state` 变为 `error` |

---

## 8. 关键约束与注意事项

1. **运行目录**：`load_config()` 默认从**当前工作目录**读取 `config.yaml` 和 `role_prompts/`，部署时确保工作目录正确，或传入绝对路径。

2. **任务生命周期**：任务状态仅保存在内存中，进程重启后丢失。如需持久化，CIO-agent 侧自行记录 `task_id` 与最终 `FinalResult`。

3. **`ai_work_dir`**：代码写入路径来自 chat_backend 项目的 `ai_work_dir` 字段，需确保该目录存在且有写权限。

4. **模型名称**：`config.yaml` 中的模型名须与 chat_backend 实际支持的模型完全匹配，否则发送消息时会报 400/404。

5. **知识库注入**：`start_task` 会自动拉取 `category_id=5` 的文档注入首条消息。若项目无知识库文档，行为不变（空注入）。

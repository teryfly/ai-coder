# agentCoderGroupLib — CIO-Agent 调用说明文档（任务类型 + 文档注入规则）

## 1. 概述

`agentCoderGroupLib` 通过 `OnboardServer` 提供异步后台任务 API。  
支持三类任务：

- `new_dev`：Architect 起步
- `formal_dev`：Engineer 起步
- `code_change`：Programmer 起步

任务状态：

- `running`
- `waiting_input`
- `done`
- `error`

---

## 2. 初始化

```python
from agentCoderGroupLib import load_config, OnboardServer

config = load_config("config.yaml")
server = OnboardServer(config)
```

---

## 3. 关键规则：引用关系不会自动进入 /messages 上下文

> 注意：`POST /v1/chat/conversations/{conversation_id}/messages` **不会自动**注入  
> 项目级/会话级 `document_references` 内容。  
> 必须显式传 `documents: [plan_documents.id...]` 才会注入到本次 LLM 上下文。

本库已在三类 Agent（Architect / Engineer / Programmer）发送消息时自动执行：

1. 查询 `GET /v1/chat/conversations/{id}/referenced-documents`
2. 合并项目级 + 会话级文档 ID
3. 发送消息时附带 `documents` 参数

因此，CIO-agent 需要做的是正确设置引用关系。

---

## 4. 引用关系 API（设置/查询）

### 4.1 项目级引用

- 查询：`GET /v1/projects/{project_id}/document-references`
- 设置：`POST /v1/projects/{project_id}/document-references`
- 清空：`DELETE /v1/projects/{project_id}/document-references`

### 4.2 会话级引用

- 查询：`GET /v1/chat/conversations/{conversation_id}/document-references`
- 设置：`POST /v1/chat/conversations/{conversation_id}/document-references`
- 清空：`DELETE /v1/chat/conversations/{conversation_id}/document-references`

### 4.3 聚合视图（用于核对）

- `GET /v1/chat/conversations/{conversation_id}/referenced-documents`

---

## 5. start_task（任务类型 + 引用参数）

```python
task_id = server.start_task(
    project_id=42,
    requirement="需求文本",
    conv_name="task-2026-03-07",
    task_type="new_dev",                 # new_dev | formal_dev | code_change
    project_document_ids=[101, 102],     # 可选：设置项目级引用（完全替换）
    conversation_document_ids=[201, 202] # 可选：设置会话级引用
)
```

---

## 6. 任务类型选择建议

| task_type | 场景 | 入口 |
|---|---|---|
| `new_dev` | 用户口述需求为主 | Architect |
| `formal_dev` | 已有规范开发文档，项目复杂 | Engineer |
| `code_change` | 既有项目变更、新增、修 bug | Programmer |

---

## 7. 推荐调用顺序（CIO-agent）

1. 获取候选文档（项目下所有 category 的计划文档）
2. 选择项目级文档和会话级文档
3. `start_task(..., project_document_ids=..., conversation_document_ids=...)`
4. 轮询 `get_status(task_id)`
5. `waiting_input` 时调用 `send_user_reply`
6. `done` 后 `get_result`

---

## 8. 轮询示例

```python
import time

task_id = server.start_task(
    project_id=42,
    requirement="修复订单并发库存问题",
    conv_name="hotfix-stock",
    task_type="code_change",
    project_document_ids=[11, 12],
    conversation_document_ids=[23],
)

while True:
    s = server.get_status(task_id)
    print(f"[{s['state']}] {s['current_agent']}: {s['message']}")

    if s["state"] == "waiting_input":
        server.send_user_reply(task_id, "continue")
    elif s["state"] in ("done", "error"):
        break

    time.sleep(3)

if s["state"] == "done":
    result = server.get_result(task_id)
    print("SUCCESS:", result.root_dir)
else:
    print("FAILED:", s["message"])
```

---

## 9. 常见问题

- `KeyError`：task_id 不存在（不是同一 server 实例）
- `ValueError`：任务尚未完成就调用 `get_result`
- `state=error`：查看 `status["message"]`
- 会话级引用与项目级引用重复：后端可能拒绝（需先去重）

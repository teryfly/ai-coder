# codeAIexecutorlib 方法调用文档

## 1. 目标与适用范围

本文档说明如何通过库的公开 API：

- 执行结构化任务文本（文件/目录/Shell 批处理）
- 获取流式执行进度
- 使用工具方法（读文件、列目录、回滚）

并覆盖 `example` 目录中所有演示能力：

1. Create file  
2. Update file  
3. Patch file  
4. Append file  
5. Insert file  
6. Delete file  
7. Move file  
8. Copy file  
9. Create folder  
10. Delete folder  
11. Execute shell command  
12. Batch operations  
13. Utility methods（read_file/list_dir/rollback_file）

---

## 2. 安装与导入

```bash
pip install -e .
```

```python
from codeAIexecutorlib import CodeExecutor, ExecutorConfig
```

---

## 3. 核心公开 API

---

### 3.1 `ExecutorConfig`

配置执行器行为（可选，不传则使用默认值）。

```python
config = ExecutorConfig(
    backup_enabled=True,      # 破坏性操作前是否自动备份
    allow_shell=True,         # 允许执行 shell 命令
    shell_timeout=300,        # 单条 shell 命令超时秒数
    verify_writes=False,      # 写入后是否回读校验
    log_level="INFO",         # 默认：ERROR；可用的过滤级别有: DEBUG, INFO, WARNING, ERROR
    log_dir="log",            # 日志目录
    max_file_size=10_485_760, # 内容上限（字节）
    max_path_length=260,      # 路径长度上限
    backup_dir=None           # 自定义备份目录，None=文件同级 .backup
)
```

---

### 3.2 `CodeExecutor(config=None, root_dir=None)`

创建执行器实例。

- `config`: `ExecutorConfig` 实例（可选）
- `root_dir`: 默认根目录（可选，实际执行时可在 `execute/read_file/...` 里传）

---

### 3.3 `execute(root_dir, content, dry_run=False) -> Generator[dict, None, None]`

**核心方法**：执行结构化任务文本，返回流式消息生成器。

- `root_dir`: 任务操作根目录（所有路径安全校验基于它）
- `content`: 任务 DSL 文本（见第 4 节）
- `dry_run`: `True` 时只校验不落盘执行

#### 返回消息结构（每次 `yield` 一个 dict）

```python
{
  "message": str,
  "type": "info|progress|success|warning|error|shell_output|summary",
  "timestamp": "ISO8601",
  "step": int,          # 可选
  "total_steps": int,   # 可选
  "data": dict          # 可选
}
```

---

### 3.4 `read_file(root_dir, file_path) -> str`

读取文件内容（通过路径安全校验）。  
失败会抛异常（不是流式 error）。

---

### 3.5 `list_dir(root_dir, dir_path=".") -> list[dict]`

列目录条目，返回：

```python
[
  {"name": "src", "type": "dir", "size": 0},
  {"name": "main.py", "type": "file", "size": 1234}
]
```

失败抛异常。

---

### 3.6 `rollback_file(root_dir, file_path) -> OperationResult`

回滚到最近备份，返回：

```python
OperationResult(
  success=True/False,
  message="...",
  error=None/"...",
  backup_path=None,
  data=None
)
```

---

## 4. 任务 DSL（`execute` 的 `content`）

每个任务块基本格式：

```text
Step [1/1] - 描述
Action: Create file
File Path: example/output/a.txt

?```text
文件内容
```

```
多个任务块用**恰好 6 个短横线**分隔：

?```text
------
```

---

### 4.1 支持的 Action（标准值）

- `Create file`
- `Update file`
- `Patch file`
- `Append to file`
- `Insert in file`
- `Delete file`
- `Move file`
- `Copy file`
- `Create folder`
- `Delete folder`
- `Execute shell command`

> 大小写不敏感；有部分别名（如 `mkdir`, `run command`）可被归一化。

---

### 4.2 各 Action 必填字段

| Action                | 必填字段                | 内容块              |
| --------------------- | ----------------------- | ------------------- |
| Create file           | File Path               | 需要                |
| Update file           | File Path               | 需要                |
| Patch file            | File Path               | 需要（patch 格式）  |
| Append to file        | File Path               | 需要                |
| Insert in file        | File Path + `Line: N`   | 需要                |
| Delete file           | File Path               | 不需要              |
| Move file             | File Path + Destination | 不需要              |
| Copy file             | File Path + Destination | 不需要              |
| Create folder         | File Path               | 不需要              |
| Delete folder         | File Path               | 不需要              |
| Execute shell command | 无 File Path 要求       | 需要（bash 代码块） |

---

### 4.3 可选字段

- `Destination: ...`（move/copy 必需）
- `Line: 3`（insert 必需）
- `Condition: if_exists | if_not_exists`

---

### 4.4 Patch 内容格式

```text
<<<< SEARCH
原文本
==== REPLACE
新文本
>>>>
```

可写多个块，按顺序一次替换一个匹配。

---

## 5. 第三方最小集成模板（推荐）

```python
from codefileexecutorlib import CodeExecutor

def run_tasks(root_dir: str, task_text: str):
    executor = CodeExecutor()
    summary = None

    for msg in executor.execute(root_dir, task_text):
        print(f"[{msg['type']}] {msg['message']}")
        if msg["type"] == "summary":
            summary = msg.get("data", {})

    return summary
```

---

## 6. 如何覆盖 example 的 13 个 Demo

你只需要为每个 demo 组装对应 DSL 文本并调用 `execute`。下面是调用要点：

1. **Create file**：`Action: Create file` + 代码块  
2. **Update file**：先 create，再 `Action: Update file` 覆盖  
3. **Patch file**：先 create，再 `Action: Patch file` + SEARCH/REPLACE  
4. **Append file**：先 create，再 `Action: Append to file`  
5. **Insert file**：先 create，再 `Action: Insert in file` + `Line: N`  
6. **Delete file**：create 后 `Action: Delete file`  
7. **Move file**：create 后 `Action: Move file` + `Destination`  
8. **Copy file**：create 后 `Action: Copy file` + `Destination`  
9. **Create folder**：`Action: Create folder`（可多步创建嵌套结构）  
10. **Delete folder**：先创建目录和文件，再 `Action: Delete folder`  
11. **Shell**：`Action: Execute shell command` + bash 代码块  
12. **Batch**：把多 action 用 `------` 串成一个 content 一次执行  
13. **Utility**：`read_file`、`list_dir`、`rollback_file`

---

## 7. Utility 方法调用示例（对应 Demo 13）

```python
from codefileexecutorlib import CodeExecutor

executor = CodeExecutor()

# 1) 先通过 execute 创建/更新文件
task = """
Step [1/1] - Create test file
Action: Create file
File Path: example/output/utility_test.txt

```text
Original
```

"""
for _ in executor.execute(".", task):
    pass

# 2) read_file

content = executor.read_file(".", "example/output/utility_test.txt")

# 3) list_dir

entries = executor.list_dir(".", "example/output")

# 4) rollback_file（需要此前发生过会创建备份的操作，如 update/patch/append/insert/delete/move）

result = executor.rollback_file(".", "example/output/utility_test.txt")
print(result.success, result.message)

```

---

## 8. 安全与限制

1. **路径安全**：所有路径必须在 `root_dir` 内（realpath 校验，防穿越）  
2. **文件名安全**：basename 仅允许 `[\w.\-]`  
3. **路径长度限制**：默认 260  
4. **内容大小限制**：默认 10MB  
5. **shell 危险命令拦截**：如 `rm -rf /`、`shutdown` 等  
6. **shell 可总开关关闭**：`allow_shell=False`

---

## 9. 常见集成建议

- 生产环境先 `dry_run=True` 预检，再正式执行
- 始终消费到 `summary` 消息，便于统计成功率
- 对 `read_file/list_dir` 使用 `try/except`
- 保留日志目录 `log/`，便于审计
- 对用户输入的 DSL 做前置校验（尤其是 action/path/destination）

---

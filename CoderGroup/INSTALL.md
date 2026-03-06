# agentCoderGroupLib — 安装部署文档

## 1. 系统要求

| 项目 | 最低要求 |
|------|---------|
| Python | 3.10+ |
| 操作系统 | Linux / macOS / Windows |
| 网络 | 可访问 chat_backend 服务 |
| 磁盘 | 50 MB（不含项目工作目录） |

---

## 2. 目录结构

部署完成后，项目根目录结构如下：

```
agentCoderGroupLib/                  ← 项目根目录
├── config.yaml                      ← 主配置文件（必须修改）
├── requirements.txt
├── setup.py
├── role_prompts/
│   ├── architect.md                 ← Architect 系统提示词
│   ├── engineer.md                  ← Engineer 系统提示词
│   └── programmer.md                ← Programmer 系统提示词
└── agentCoderGroupLib/              ← Python 包
    └── ...
```

---

## 3. 安装步骤

### 3.1 获取源码

```bash
# 克隆主库
git clone <agentCoderGroupLib 仓库地址>
cd agentCoderGroupLib

# 克隆执行器依赖库
git clone https://github.com/teryfly/ai-coder.git /opt/ai-coder
```

### 3.2 安装依赖

```bash
# 安装执行器库（codeAIexecutorlib）
pip install -e /opt/ai-coder

# 安装其余依赖
pip install requests pyyaml
```

### 3.3 安装本库（可选，用于全局命令）

```bash
pip install -e .
```

安装后可直接在任意目录使用命令行工具：

```bash
agentcoder
```

---

## 4. 配置文件

编辑项目根目录下的 `config.yaml`：

```yaml
chat_backend:
  url: "http://<your-host>:<port>"     # chat_backend 服务地址
  token: "sk-test-xxxxxxxxxxxxxxxx"    # Bearer Token（sk-test 或 poe-sk 开头）

max_files_per_run: 20                  # 单次任务最大文件数，超过则路由至 Engineer

agents:
  architect:
    model: "GPT-5.3-Codex"
    prompt_file: "role_prompts/architect.md"
  engineer:
    model: "GPT-5.3-Codex"
    prompt_file: "role_prompts/engineer.md"
  programmer:
    model: "GPT-5.3-Codex"
    prompt_file: "role_prompts/programmer.md"
```

### 配置项说明

| 配置项 | 说明 |
|--------|------|
| `chat_backend.url` | chat_backend 服务的 Base URL，不带尾部斜线 |
| `chat_backend.token` | 鉴权 Token，须以 `sk-test` 或 `poe-sk` 开头 |
| `max_files_per_run` | 任务路由阈值。估算文件数 < 此值 → Programmer；≥ 此值 → Engineer（再分解） |
| `agents.*.model` | 各 Agent 使用的 LLM 模型名称，需与 chat_backend 支持的模型一致 |
| `agents.*.prompt_file` | 系统提示词文件路径，相对于运行目录 |

---

## 5. 验证安装

在项目根目录下运行：

```bash
python -c "from agentCoderGroupLib import OnboardServer, ConsoleRunner; print('PASS')"
```

输出 `PASS` 即表示安装成功。

---

## 6. 运行方式

### 6.1 交互式控制台

```bash
# 必须在项目根目录运行，以便读取 config.yaml 和 role_prompts/
python -m agentCoderGroupLib.entry.console_runner
# 或安装后使用
agentcoder
```

控制台会引导你：
1. 选择项目
2. 选择已有会话或新建会话
3. 输入编码需求
4. 全程自动运行，仅在 Agent 提问时暂停等待输入

### 6.2 作为库调用（供 CIO-agent 集成）

```python
from agentCoderGroupLib import load_config, OnboardServer

config = load_config("path/to/config.yaml")
server = OnboardServer(config)
```

详细调用方式见 `CIO_AGENT_GUIDE.md`。

---

## 7. 运行目录要求

**所有运行方式均需在包含 `config.yaml` 的目录下执行**，因为：

- `load_config()` 默认读取当前目录的 `config.yaml`
- `load_prompt()` 按配置文件中的相对路径加载 `role_prompts/*.md`

若需在其他目录运行，可传入绝对路径：

```python
config = load_config("/absolute/path/to/config.yaml")
```

---

## 8. 日志与备份

- 执行日志：由 `codeAiExecutorLib` 写入 `log/` 目录（相对于 `ai_work_dir`）
- 文件备份：破坏性操作前自动备份至 `.backup/` 目录（`backup_enabled=True`）
- 可通过 `CodeExecutorAdapter(log_level="DEBUG")` 开启详细日志

---

## 9. 常见问题

**Q: `config.yaml` 找不到**
A: 确认在项目根目录（含 `config.yaml` 的目录）下运行。

**Q: `ImportError: No module named 'codeAiExecutorLib'`**
A: 执行 `pip install -e /opt/ai-coder` 安装执行器库。

**Q: 鉴权失败 401**
A: 检查 `config.yaml` 中 `token` 是否以 `sk-test` 或 `poe-sk` 开头。

**Q: Agent 一直循环不终止**
A: 检查 LLM 模型是否返回了正确的终止行格式。可临时调低 `max_files_per_run` 以路由至 Programmer 快速验证。

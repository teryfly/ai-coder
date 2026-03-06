import os
from dataclasses import dataclass

import yaml


@dataclass
class AgentConfig:
    model: str
    prompt_file: str


@dataclass
class AppConfig:
    chat_backend_url: str
    chat_backend_token: str
    max_files_per_run: int
    architect: AgentConfig
    engineer: AgentConfig
    programmer: AgentConfig


def load_config(path: str = "config.yaml") -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    chat_backend = data.get("chat_backend", {})
    max_files = data.get("max_files_per_run", 20)
    agents_data = data.get("agents", {})

    def _agent(key: str) -> AgentConfig:
        ag = agents_data.get(key, {})
        return AgentConfig(
            model=ag.get("model", "claude-sonnet-4-20250514"),
            prompt_file=ag.get("prompt_file", f"role_prompts/{key}.md"),
        )

    return AppConfig(
        chat_backend_url=chat_backend.get("url", "http://localhost:8000"),
        chat_backend_token=chat_backend.get("token", ""),
        max_files_per_run=int(max_files),
        architect=_agent("architect"),
        engineer=_agent("engineer"),
        programmer=_agent("programmer"),
    )


def load_prompt(prompt_file: str) -> str:
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()

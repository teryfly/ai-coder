from abc import ABC, abstractmethod

from ..adapters.chat_backend_client import ChatBackendClient
from ..config.app_config import AppConfig, load_prompt


class BaseAgent(ABC):
    def __init__(
        self,
        client: ChatBackendClient,
        config: AppConfig,
        project_id: int,
        conv_name: str,
        agent_key: str,
    ):
        self._client = client
        self._config = config
        self._project_id = project_id

        agent_cfg = getattr(config, agent_key)
        self._model = agent_cfg.model
        self._system_prompt = load_prompt(agent_cfg.prompt_file)

        self._conv_id = client.create_conversation(
            project_id=project_id,
            name=conv_name,
            system_prompt=self._system_prompt,
            model=self._model,
        )
        self._history: list[dict] = []
        self._last_reply: str = ""

    def send(self, message: str) -> str:
        reply = self._client.send_message(self._conv_id, message, self._model)
        self._history.append({"role": "user", "content": message})
        self._history.append({"role": "assistant", "content": reply})
        self._last_reply = reply
        return reply

    def get_last_reply(self) -> str:
        return self._last_reply

    def get_history(self) -> list[dict]:
        return list(self._history)

    @property
    def conversation_id(self) -> str:
        return self._conv_id

    @abstractmethod
    def is_complete(self, reply: str) -> bool:
        pass

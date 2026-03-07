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
        conversation_document_ids: list[int] | None = None,
        conversation_id: str | None = None,
    ):
        self._client = client
        self._config = config
        self._project_id = project_id
        self._agent_key = agent_key

        agent_cfg = getattr(config, agent_key)
        self._model = agent_cfg.model
        self._system_prompt = load_prompt(agent_cfg.prompt_file)

        if conversation_id:
            self._conv_id = conversation_id
        else:
            # Use configured agent key as assistance role (e.g. architect/engineer/programmer),
            # instead of model name.
            self._conv_id = client.create_conversation(
                project_id=project_id,
                name=conv_name,
                system_prompt=self._system_prompt,
                model=self._model,
                assistance_role=self._agent_key,
            )

        if conversation_document_ids:
            self._client.set_conversation_document_references(
                self._conv_id, [int(x) for x in conversation_document_ids]
            )

        # Cache context documents (project-level + conversation-level).
        self._context_document_ids: list[int] = self._load_context_document_ids()

        self._history: list[dict] = []
        self._last_reply: str = ""

    def _load_context_document_ids(self) -> list[int]:
        refs = self._client.get_referenced_documents(self._conv_id)
        if not isinstance(refs, dict):
            return []

        ids: list[int] = []
        seen: set[int] = set()
        for section in ("project_references", "conversation_references"):
            for item in refs.get(section, []) or []:
                if not isinstance(item, dict):
                    continue
                value = item.get("document_id")
                if value is None:
                    continue
                doc_id = int(value)
                if doc_id in seen:
                    continue
                seen.add(doc_id)
                ids.append(doc_id)
        return ids

    def send(self, message: str) -> str:
        # Explicitly inject referenced document IDs on every call.
        reply = self._client.send_message(
            self._conv_id,
            message,
            self._model,
            documents=self._context_document_ids,
        )
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
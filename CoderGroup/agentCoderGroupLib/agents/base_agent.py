from abc import ABC, abstractmethod
from typing import Callable, Generator

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
        base_prompt = load_prompt(agent_cfg.prompt_file)

        if hasattr(self, "_augment_system_prompt"):
            self._system_prompt = self._augment_system_prompt(base_prompt, project_id)
        else:
            self._system_prompt = base_prompt

        if conversation_id:
            self._conv_id = conversation_id
        else:
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

    def send_stream(
        self, 
        message: str, 
        on_chunk: Callable[[str, int, bool], None] | None = None
    ) -> Generator[tuple[str, int, bool], None, str]:
        """
        Send message with streaming and yield chunks.
        
        Args:
            message: Message to send
            on_chunk: Optional callback(chunk_text, line_count, is_final)
        
        Yields:
            tuple[chunk_text, line_count, is_final]
        
        Returns:
            Complete accumulated reply
        """
        accumulated = ""
        line_count = 0
        
        for chunk_text, is_final in self._client.send_message_stream(
            self._conv_id,
            message,
            self._model,
            documents=self._context_document_ids,
        ):
            accumulated += chunk_text
            line_count = accumulated.count('\n') + 1
            
            if on_chunk:
                on_chunk(chunk_text, line_count, is_final)
            
            yield chunk_text, line_count, is_final
        
        self._history.append({"role": "user", "content": message})
        self._history.append({"role": "assistant", "content": accumulated})
        self._last_reply = accumulated
        
        return accumulated

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
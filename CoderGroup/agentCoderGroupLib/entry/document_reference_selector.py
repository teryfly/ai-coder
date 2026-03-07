from __future__ import annotations

from dataclasses import dataclass

from ..adapters.chat_backend_client import ChatBackendClient, ChatBackendError
from .console_ui import ConsoleUI


@dataclass(frozen=True)
class DocumentItem:
    index: int
    document_id: int
    filename: str
    category_id: int
    version: int


class DocumentReferenceSelector:
    def __init__(self, client: ChatBackendClient, ui: ConsoleUI):
        self._client = client
        self._ui = ui

    def choose_project_level_references(self, project_id: int) -> list[int]:
        docs = self._load_all_docs(project_id)
        if not docs:
            self._ui.append_output("No plan documents found in this project. Skip project-level references.")
            return []

        self._ui.set_output(self._render_group("Project documents (all categories)", docs))
        self._ui.set_info(["Select project-level references.", "Input: 1,3,5 | all | skip"])
        cmd = self._ui.prompt_input("Project reference selection: ")
        if ConsoleUI.is_exit_command(cmd):
            raise SystemExit(0)

        selected = self._parse_selection(cmd, docs)
        if selected is None:
            self._ui.append_output("Invalid selection. Skip project-level references.")
            return []
        return selected

    def choose_conversation_level_references(self, project_id: int, conversation_id: str) -> list[int]:
        docs = self._load_all_docs(project_id)
        if not docs:
            self._ui.append_output("No plan documents found in this project. Skip conversation-level references.")
            return []

        project_ref_ids = self._load_project_reference_ids(project_id)
        conversation_ref_ids = self._load_conversation_reference_ids(conversation_id)

        project_docs = [d for d in docs if d.document_id in project_ref_ids]
        conversation_docs = [d for d in docs if d.document_id in conversation_ref_ids]
        others = [
            d
            for d in docs
            if d.document_id not in project_ref_ids and d.document_id not in conversation_ref_ids
        ]

        lines: list[str] = []
        lines.extend(self._render_group("Referenced (project-level)", project_docs))
        lines.append("")
        lines.extend(self._render_group("Referenced (conversation-level)", conversation_docs))
        lines.append("")
        lines.extend(self._render_group("Other documents (selectable for conversation-level)", others))

        self._ui.set_output(lines)
        self._ui.set_info(
            [
                "Select conversation-level references from 'Other documents'.",
                "Input: 1,3,5 | all | skip",
            ]
        )

        if not others:
            self._ui.append_output("No selectable documents. Skip conversation-level references.")
            return []

        cmd = self._ui.prompt_input("Conversation reference selection: ")
        if ConsoleUI.is_exit_command(cmd):
            raise SystemExit(0)

        selected = self._parse_selection(cmd, others)
        if selected is None:
            self._ui.append_output("Invalid selection. Skip conversation-level references.")
            return []
        return selected

    def render_project_references(self, project_id: int) -> list[str]:
        docs = self._load_all_docs(project_id)
        project_ids = self._load_project_reference_ids(project_id)
        project_docs = [d for d in docs if d.document_id in project_ids]
        return ["Current project-level references:"] + self._render_group("Project-level", project_docs)

    def render_references_for_conversation(self, project_id: int, conversation_id: str) -> list[str]:
        docs = self._load_all_docs(project_id)
        project_ids = self._load_project_reference_ids(project_id)
        conv_ids = self._load_conversation_reference_ids(conversation_id)

        project_docs = [d for d in docs if d.document_id in project_ids]
        conv_docs = [d for d in docs if d.document_id in conv_ids]

        lines = ["Current referenced documents:"]
        lines.extend(self._render_group("Project-level", project_docs))
        lines.append("")
        lines.extend(self._render_group("Conversation-level", conv_docs))
        return lines

    def _load_all_docs(self, project_id: int) -> list[DocumentItem]:
        try:
            records = self._client.list_latest_documents(project_id=project_id, category_id=None, page_size=200)
        except ChatBackendError as exc:
            self._ui.append_output(f"[Warning] Failed to load plan documents: {exc}")
            return []

        sorted_records = sorted(
            records,
            key=lambda x: (
                int(x.get("category_id", 0) or 0),
                str(x.get("filename", "")),
                -int(x.get("version", 0) or 0),
            ),
        )
        docs: list[DocumentItem] = []
        for i, item in enumerate(sorted_records, start=1):
            docs.append(
                DocumentItem(
                    index=i,
                    document_id=int(item.get("id", 0) or 0),
                    filename=str(item.get("filename", "unnamed")),
                    category_id=int(item.get("category_id", 0) or 0),
                    version=int(item.get("version", 0) or 0),
                )
            )
        return docs

    def _extract_ids_from_reference_payload(self, data: dict | list) -> set[int]:
        ids: set[int] = set()
        if isinstance(data, dict):
            for key in ("current_references", "references", "items"):
                for x in data.get(key, []) or []:
                    if isinstance(x, dict) and x.get("document_id") is not None:
                        ids.add(int(x["document_id"]))
                    elif isinstance(x, int):
                        ids.add(int(x))
        elif isinstance(data, list):
            for x in data:
                if isinstance(x, dict) and x.get("document_id") is not None:
                    ids.add(int(x["document_id"]))
                elif isinstance(x, int):
                    ids.add(int(x))
        return ids

    def _load_project_reference_ids(self, project_id: int) -> set[int]:
        try:
            payload = self._client.get_project_document_references(project_id)
        except ChatBackendError as exc:
            self._ui.append_output(f"[Warning] Failed to load project document references: {exc}")
            return set()
        return self._extract_ids_from_reference_payload(payload)

    def _load_conversation_reference_ids(self, conversation_id: str) -> set[int]:
        try:
            payload = self._client.get_conversation_document_references(conversation_id)
        except ChatBackendError as exc:
            self._ui.append_output(f"[Warning] Failed to load conversation document references: {exc}")
            return set()
        return self._extract_ids_from_reference_payload(payload)

    def _render_group(self, title: str, docs: list[DocumentItem]) -> list[str]:
        lines = [f"{title}:"]
        if not docs:
            lines.append("  (none)")
            return lines
        for i, d in enumerate(docs, start=1):
            lines.append(f"  {i}. {d.filename} (doc_id={d.document_id}, cat={d.category_id}, v={d.version})")
        return lines

    def _parse_selection(self, raw: str, docs: list[DocumentItem]) -> list[int] | None:
        text = (raw or "").strip().lower()
        if text in {"", "skip", "s"}:
            return []
        if text == "all":
            return [x.document_id for x in docs]

        chunks = [x.strip() for x in text.split(",") if x.strip()]
        if not chunks:
            return []

        ids: list[int] = []
        seen: set[int] = set()
        for ch in chunks:
            if not ch.isdigit():
                return None
            idx = int(ch)
            if idx < 1 or idx > len(docs):
                return None
            doc_id = docs[idx - 1].document_id
            if doc_id not in seen:
                seen.add(doc_id)
                ids.append(doc_id)
        return ids
import requests


class ChatBackendError(Exception):
    pass


class ChatBackendClient:
    def __init__(self, base_url: str, token: str):
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def _extract_error_detail(self, resp: requests.Response) -> str:
        """Safely parse backend error payloads that may be dict/list/plain text."""
        if not resp.content:
            return resp.text or "unknown error"

        try:
            payload = resp.json()
        except ValueError:
            return resp.text or "unknown error"

        if isinstance(payload, dict):
            detail = payload.get("detail", payload)
        else:
            detail = payload
        return str(detail)

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self._base_url}{path}"
        resp = self._session.get(url, params=params)
        if not resp.ok:
            detail = self._extract_error_detail(resp)
            raise ChatBackendError(f"GET {path} failed ({resp.status_code}): {detail}")
        return resp.json()

    def _post(self, path: str, body: dict = None) -> dict:
        url = f"{self._base_url}{path}"
        resp = self._session.post(url, json=body or {})
        if not resp.ok:
            detail = self._extract_error_detail(resp)
            raise ChatBackendError(f"POST {path} failed ({resp.status_code}): {detail}")
        return resp.json()

    def _put(self, path: str, body: dict = None) -> dict:
        url = f"{self._base_url}{path}"
        resp = self._session.put(url, json=body or {})
        if not resp.ok:
            detail = self._extract_error_detail(resp)
            raise ChatBackendError(f"PUT {path} failed ({resp.status_code}): {detail}")
        return resp.json()

    # --- Projects ---

    def list_projects(self) -> list[dict]:
        data = self._get("/v1/projects")
        items = data if isinstance(data, list) else data.get("projects", [])
        return sorted(items, key=lambda p: p.get("updated_time", ""), reverse=True)

    def get_project(self, project_id: int) -> dict:
        return self._get(f"/v1/projects/{project_id}")

    # --- Conversations ---

    def list_conversations(self, project_id: int) -> list[dict]:
        data = self._get("/v1/chat/conversations", params={"project_id": project_id})
        items = data if isinstance(data, list) else data.get("conversations", data)
        return sorted(items, key=lambda c: c.get("updated_at", ""), reverse=True)

    def create_conversation(
        self, project_id: int, name: str, system_prompt: str, model: str
    ) -> str:
        data = self._post(
            "/v1/chat/conversations",
            {
                "project_id": project_id,
                "name": name,
                "system_prompt": system_prompt,
                "model": model,
            },
        )
        return data["conversation_id"]

    def get_conversation(self, conv_id: str) -> dict:
        return self._get(f"/v1/chat/conversations/{conv_id}")

    def update_conversation(self, conv_id: str, **kwargs) -> None:
        self._put(f"/v1/chat/conversations/{conv_id}", kwargs)

    # --- Messages ---

    def get_messages(self, conv_id: str) -> list[dict]:
        data = self._get(f"/v1/chat/conversations/{conv_id}/messages")
        if isinstance(data, dict):
            return data.get("messages", [])
        return data

    def send_message(
        self, conv_id: str, content: str, model: str, stream: bool = False
    ) -> str:
        data = self._post(
            f"/v1/chat/conversations/{conv_id}/messages",
            {"role": "user", "content": content, "model": model, "stream": stream},
        )
        return data.get("reply", "")

    # --- Knowledge / Documents ---

    def _latest_docs_from_history(self, project_id: int, category_id: int) -> list[dict]:
        """Fallback for backends where /documents/latest is unavailable or mis-routed."""
        data = self._get(
            "/v1/plan/documents/history",
            params={"project_id": project_id, "category_id": category_id},
        )
        records = data if isinstance(data, list) else data.get("items", [])

        latest_by_filename: dict[str, dict] = {}
        for doc in records:
            filename = str(doc.get("filename", "")).strip()
            if not filename:
                continue

            existing = latest_by_filename.get(filename)
            current_ver = int(doc.get("version", 0) or 0)
            existing_ver = int(existing.get("version", 0) or 0) if existing else -1

            if existing is None or current_ver >= existing_ver:
                latest_by_filename[filename] = doc

        return list(latest_by_filename.values())

    def get_knowledge_docs(self, project_id: int) -> list[dict]:
        """
        Preferred endpoint: /v1/plan/documents/latest
        Fallback endpoint: /v1/plan/documents/history (older/misconfigured backends)
        """
        try:
            data = self._get(
                "/v1/plan/documents/latest",
                params={"project_id": project_id, "category_id": 5},
            )
            return data.get("items", []) if isinstance(data, dict) else []
        except ChatBackendError as exc:
            message = str(exc).lower()
            # FastAPI route-order issue symptom:
            # /documents/latest got matched by /documents/{document_id}
            if "documents/latest" in message and "int_parsing" in message:
                return self._latest_docs_from_history(project_id=project_id, category_id=5)
            raise

    def get_referenced_documents(self, conv_id: str) -> dict:
        return self._get(f"/v1/chat/conversations/{conv_id}/referenced-documents")

    def get_project_source_code(self, project_id: int) -> str:
        data = self._get(f"/v1/projects/{project_id}/complete-source-code")
        return data.get("completeSourceCode", "")
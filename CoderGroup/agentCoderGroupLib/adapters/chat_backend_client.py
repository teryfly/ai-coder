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
        if not resp.content:
            return resp.text or "unknown error"
        try:
            payload = resp.json()
        except ValueError:
            return resp.text or "unknown error"
        if isinstance(payload, dict):
            payload = payload.get("detail", payload)
        return str(payload)

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = self._session.get(f"{self._base_url}{path}", params=params)
        if not resp.ok:
            detail = self._extract_error_detail(resp)
            raise ChatBackendError(f"GET {path} failed ({resp.status_code}): {detail}")
        return resp.json()

    def _post(self, path: str, body: dict | None = None) -> dict:
        resp = self._session.post(f"{self._base_url}{path}", json=body or {})
        if not resp.ok:
            detail = self._extract_error_detail(resp)
            raise ChatBackendError(f"POST {path} failed ({resp.status_code}): {detail}")
        return resp.json()

    def _put(self, path: str, body: dict | None = None) -> dict:
        resp = self._session.put(f"{self._base_url}{path}", json=body or {})
        if not resp.ok:
            detail = self._extract_error_detail(resp)
            raise ChatBackendError(f"PUT {path} failed ({resp.status_code}): {detail}")
        return resp.json()

    def _delete(self, path: str) -> dict:
        resp = self._session.delete(f"{self._base_url}{path}")
        if not resp.ok:
            detail = self._extract_error_detail(resp)
            raise ChatBackendError(f"DELETE {path} failed ({resp.status_code}): {detail}")
        return resp.json() if resp.content else {}

    # --- Projects ---

    def list_projects(self) -> list[dict]:
        data = self._get("/v1/projects")
        items = data if isinstance(data, list) else data.get("projects", [])
        return sorted(items, key=lambda p: p.get("updated_time", ""), reverse=True)

    def get_project(self, project_id: int) -> dict:
        return self._get(f"/v1/projects/{project_id}")

    def create_project(
        self,
        name: str,
        ai_work_dir: str = "/aiWorkDir",
        dev_environment: str = "python3.11",
        grpc_server_address: str = "127.0.0.1:50051",
    ) -> dict:
        body = {
            "name": name,
            "ai_work_dir": ai_work_dir,
            "dev_environment": dev_environment,
            "grpc_server_address": grpc_server_address,
        }
        return self._post("/v1/projects", body)

    # --- Conversations ---

    def list_conversations(self, project_id: int) -> list[dict]:
        data = self._get("/v1/chat/conversations", params={"project_id": project_id})
        items = data if isinstance(data, list) else data.get("conversations", data)
        return sorted(items, key=lambda c: c.get("updated_at", ""), reverse=True)

    def create_conversation(
        self,
        project_id: int,
        name: str,
        system_prompt: str,
        model: str,
        assistance_role: str | None = None,
    ) -> str:
        body = {
            "project_id": project_id,
            "name": name,
            "system_prompt": system_prompt,
            "model": model,
        }
        if assistance_role:
            body["assistance_role"] = assistance_role
        return self._post("/v1/chat/conversations", body)["conversation_id"]

    def get_conversation(self, conv_id: str) -> dict:
        return self._get(f"/v1/chat/conversations/{conv_id}")

    def update_conversation(self, conv_id: str, **kwargs) -> None:
        self._put(f"/v1/chat/conversations/{conv_id}", kwargs)

    # --- Messages ---

    def get_messages(self, conv_id: str) -> list[dict]:
        data = self._get(f"/v1/chat/conversations/{conv_id}/messages")
        return data.get("messages", []) if isinstance(data, dict) else data

    def send_message(
        self,
        conv_id: str,
        content: str,
        model: str,
        stream: bool = False,
        documents: list[int] | None = None,
    ) -> str:
        body: dict = {"role": "user", "content": content, "model": model, "stream": stream}
        if documents:
            body["documents"] = [int(x) for x in documents]
        data = self._post(f"/v1/chat/conversations/{conv_id}/messages", body)
        return data.get("reply", "")

    # --- Plan Documents ---

    def _latest_docs_from_history(
        self, project_id: int, category_id: int | None = None
    ) -> list[dict]:
        params: dict[str, int] = {"project_id": project_id}
        if category_id is not None:
            params["category_id"] = category_id
        data = self._get("/v1/plan/documents/history", params=params)
        records = data if isinstance(data, list) else data.get("items", [])
        latest: dict[str, dict] = {}
        for doc in records:
            filename = str(doc.get("filename", "")).strip()
            if not filename:
                continue
            old = latest.get(filename)
            old_v = int(old.get("version", 0) or 0) if old else -1
            cur_v = int(doc.get("version", 0) or 0)
            if old is None or cur_v >= old_v:
                latest[filename] = doc
        return list(latest.values())

    def list_latest_documents(
        self, project_id: int, category_id: int | None = None, page_size: int = 200
    ) -> list[dict]:
        params: dict[str, int | str] = {
            "project_id": project_id,
            "page": 1,
            "page_size": max(1, min(page_size, 200)),
            "sort_by": "created_time",
            "order": "desc",
        }
        if category_id is not None:
            params["category_id"] = category_id

        all_items: list[dict] = []
        while True:
            try:
                data = self._get("/v1/plan/documents/latest", params=params)
            except ChatBackendError as exc:
                msg = str(exc).lower()
                if "documents/latest" in msg and "int_parsing" in msg:
                    return self._latest_docs_from_history(project_id, category_id)
                raise

            items = data.get("items", []) if isinstance(data, dict) else []
            all_items.extend(items)
            total = int(data.get("total", len(all_items))) if isinstance(data, dict) else len(all_items)
            if len(all_items) >= total or not items:
                break
            params["page"] = int(params["page"]) + 1
        return all_items

    def get_knowledge_docs(self, project_id: int) -> list[dict]:
        return self.list_latest_documents(project_id=project_id, category_id=5, page_size=200)

    # --- Document References ---

    def get_project_document_references(self, project_id: int) -> dict:
        return self._get(f"/v1/projects/{project_id}/document-references")

    def set_project_document_references(self, project_id: int, document_ids: list[int]) -> dict:
        return self._post(
            f"/v1/projects/{project_id}/document-references",
            {"document_ids": [int(x) for x in document_ids]},
        )

    def clear_project_document_references(self, project_id: int) -> dict:
        return self._delete(f"/v1/projects/{project_id}/document-references")

    def get_conversation_document_references(self, conv_id: str) -> dict:
        return self._get(f"/v1/chat/conversations/{conv_id}/document-references")

    def set_conversation_document_references(self, conv_id: str, document_ids: list[int]) -> dict:
        return self._post(
            f"/v1/chat/conversations/{conv_id}/document-references",
            {"document_ids": [int(x) for x in document_ids]},
        )

    def clear_conversation_document_references(self, conv_id: str) -> dict:
        return self._delete(f"/v1/chat/conversations/{conv_id}/document-references")

    def get_referenced_documents(self, conv_id: str) -> dict:
        return self._get(f"/v1/chat/conversations/{conv_id}/referenced-documents")

    def get_project_source_code(self, project_id: int) -> str:
        data = self._get(f"/v1/projects/{project_id}/complete-source-code")
        return data.get("completeSourceCode", "")
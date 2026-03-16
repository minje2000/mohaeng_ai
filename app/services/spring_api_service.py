from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class SpringApiService:
    def __init__(self) -> None:
        self.base_url = settings.SPRING_API_BASE_URL.rstrip("/")
        self.timeout = httpx.Timeout(20.0, connect=10.0)

    def _headers(self, authorization: str | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if authorization:
            headers["Authorization"] = authorization
        return headers

    async def _get(self, path: str, *, authorization: str | None = None, params: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            res = await client.get(path, headers=self._headers(authorization), params=params)
            res.raise_for_status()
            return res.json()

    async def _post(self, path: str, *, authorization: str | None = None, json_body: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            res = await client.post(path, headers={**self._headers(authorization), "Content-Type": "application/json"}, json=json_body or {})
            res.raise_for_status()
            return res.json() if res.content else {}

    def _extract_list(self, data: Any) -> list[dict]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("content", "items", "list", "data", "result"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
                if isinstance(value, dict):
                    nested = self._extract_list(value)
                    if nested:
                        return nested
        return []

    def _extract_dict(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            if "data" in data and isinstance(data.get("data"), dict):
                return data["data"]
            return data
        return {}

    async def search_events(self, *, keyword: str | None = None, region_id: int | None = None, hide_closed: bool = True, event_status: str | None = None, page: int = 0, size: int = 12) -> list[dict]:
        params: dict[str, Any] = {
            "page": page,
            "size": size,
            "hideClosed": str(hide_closed).lower(),
        }
        if keyword:
            params["keyword"] = keyword
        if region_id:
            params["regionId"] = region_id
        if event_status:
            params["eventStatus"] = event_status

        data = await self._get("/api/events/search", params=params)
        return self._extract_list(data)

    async def recommend_events(self, authorization: str | None = None) -> list[dict]:
        data = await self._get("/api/events/recommend", authorization=authorization)
        return self._extract_list(data)

    async def get_my_inquiries(self, authorization: str) -> dict:
        data = await self._get(
            "/api/eventInquiry/mypage",
            authorization=authorization,
            params={"tab": "ALL", "page": 0, "size": 5},
        )
        return self._extract_dict(data)

    async def get_my_participations(self, authorization: str) -> list[dict]:
        data = await self._get("/api/mypage/events/participations", authorization=authorization)
        return self._extract_list(data)

    async def get_my_wishlist(self, authorization: str) -> list[dict]:
        data = await self._get(
            "/api/user/wishlist",
            authorization=authorization,
            params={"page": 0, "size": 6},
        )
        return self._extract_list(data)

    async def get_public_faqs(self) -> list[dict]:
        try:
            data = await self._get("/api/ai/faqs/public")
        except Exception:
            return []
        return self._extract_list(data)

    async def submit_admin_contact(self, *, session_id: str | None, content: str, authorization: str | None = None) -> dict:
        try:
            data = await self._post(
                "/api/ai/admin-contacts",
                authorization=authorization,
                json_body={"sessionId": session_id, "content": content},
            )
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

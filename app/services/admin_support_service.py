
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data' / 'chatbot'
CONTACTS_PATH = DATA_DIR / 'admin-contacts.json'


class AdminSupportService:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _read_json(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return []
        return payload if isinstance(payload, list) else []

    def _write_json(self, path: Path, items: list[dict[str, Any]]) -> None:
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')

    def _now(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')

    def save_contact(
        self,
        *,
        content: str,
        session_id: str | None = None,
        authorization: str | None = None,
        source: str = 'chatbot',
    ) -> dict[str, Any]:
        items = self._read_json(CONTACTS_PATH)
        row = {
            'id': str(uuid4()),
            'content': content.strip(),
            'status': '대기',
            'createdAt': self._now(),
            'sessionId': session_id or '',
            'hasAuthorization': bool(authorization),
            'source': source,
            'answer': '',
            'memo': '',
            'assignee': '',
            'category': '',
            'priority': '',
        }
        items.insert(0, row)
        self._write_json(CONTACTS_PATH, items[:500])
        return row

    def list_contacts(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self._read_json(CONTACTS_PATH)[: max(1, min(limit, 500))]

    def update_contact(
        self,
        *,
        item_id: str,
        answer: str | None = None,
        status: str | None = None,
        assignee: str | None = None,
        category: str | None = None,
        priority: str | None = None,
        memo: str | None = None,
        actor: str | None = None,
    ) -> dict[str, Any] | None:
        items = self._read_json(CONTACTS_PATH)
        updated = None
        for item in items:
            if str(item.get('id')) != str(item_id):
                continue
            if answer is not None:
                item['answer'] = answer.strip()
            if status is not None:
                item['status'] = status.strip() or item.get('status') or '대기'
            if assignee is not None:
                item['assignee'] = assignee.strip()
            if category is not None:
                item['category'] = category.strip()
            if priority is not None:
                item['priority'] = priority.strip()
            if memo is not None:
                item['memo'] = memo.strip()
            item['updatedAt'] = self._now()
            item['updatedBy'] = (actor or '관리자').strip()
            if answer is not None and answer.strip():
                item['answeredAt'] = self._now()
                if not item.get('status'):
                    item['status'] = '답변완료'
            updated = item
            break
        if updated is not None:
            self._write_json(CONTACTS_PATH, items)
        return updated

    def delete_contact(self, *, item_id: str) -> bool:
        items = self._read_json(CONTACTS_PATH)
        next_items = [item for item in items if str(item.get('id')) != str(item_id)]
        if len(next_items) == len(items):
            return False
        self._write_json(CONTACTS_PATH, next_items)
        return True

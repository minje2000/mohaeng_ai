from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


class AdminContactService:
    def __init__(self, path: str = './data/chatbot/admin-contacts.json') -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self.path.exists():
            self.path.write_text('[]', encoding='utf-8')

    def _read(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding='utf-8') or '[]')
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write(self, items: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')

    def submit(self, *, session_id: str | None, authorization: str | None, message: str) -> dict[str, Any]:
        content = str(message or '').replace('관리자 문의:', '', 1).strip()
        item = {
            'id': int(datetime.now().timestamp() * 1000),
            'createdAt': datetime.now().isoformat(timespec='seconds'),
            'sessionId': session_id,
            'authorization': authorization[:60] if authorization else None,
            'message': content,
            'status': '대기',
            'answer': '',
        }
        with self._lock:
            items = self._read()
            items.insert(0, item)
            self._write(items)
        return item

    def list_items(self) -> list[dict[str, Any]]:
        with self._lock:
            return self._read()

    def answer(self, item_id: int, answer: str, status: str = '답변완료') -> dict[str, Any] | None:
        with self._lock:
            items = self._read()
            updated = None
            for item in items:
                if int(item.get('id', 0)) == int(item_id):
                    item['answer'] = str(answer or '').strip()
                    item['status'] = status or '답변완료'
                    item['answeredAt'] = datetime.now().isoformat(timespec='seconds')
                    updated = item
                    break
            if updated is not None:
                self._write(items)
            return updated

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data' / 'chatbot'
CONTACTS_PATH = DATA_DIR / 'admin-contacts.json'
LOGS_PATH = DATA_DIR / 'chat-logs.json'


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
        path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

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
        }
        items.insert(0, row)
        self._write_json(CONTACTS_PATH, items[:500])
        return row

    def list_contacts(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self._read_json(CONTACTS_PATH)[: max(1, min(limit, 500))]

    def answer_contact(self, *, item_id: str, answer: str, status: str = '답변완료') -> dict[str, Any] | None:
        items = self._read_json(CONTACTS_PATH)
        updated = None
        for item in items:
            if str(item.get('id')) == str(item_id):
                item['answer'] = (answer or '').strip()
                item['status'] = (status or '답변완료').strip()
                item['answeredAt'] = self._now()
                updated = item
                break
        if updated is not None:
            self._write_json(CONTACTS_PATH, items)
        return updated

    def save_log(
        self,
        *,
        question: str,
        answer: str,
        intent: str | None = None,
        session_id: str | None = None,
        is_error: bool = False,
    ) -> dict[str, Any]:
        items = self._read_json(LOGS_PATH)
        row = {
            'id': str(uuid4()),
            'question': question.strip(),
            'answer': answer.strip(),
            'intent': intent or '',
            'createdAt': self._now(),
            'sessionId': session_id or '',
            'isError': bool(is_error),
        }
        items.insert(0, row)
        self._write_json(LOGS_PATH, items[:1000])
        return row

    def _normalize_admin_contact_question(self, question: str) -> str:
        text = (question or '').strip()
        prefixes = ['관리자 문의:', '관리자문의:']
        for prefix in prefixes:
            if text.startswith(prefix):
                return text.split(':', 1)[1].strip()
        return text

    def _enrich_log_session_ids(self, logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        contacts = self._read_json(CONTACTS_PATH)
        contact_session_map: dict[str, str] = {}
        for contact in contacts:
            key = (contact.get('content') or '').strip()
            session_id = (contact.get('sessionId') or '').strip()
            if key and session_id and key not in contact_session_map:
                contact_session_map[key] = session_id

        enriched: list[dict[str, Any]] = []
        for log in logs:
            item = dict(log)
            if not (item.get('sessionId') or '').strip():
                question_key = self._normalize_admin_contact_question(item.get('question') or '')
                session_id = contact_session_map.get(question_key, '')
                if session_id:
                    item['sessionId'] = session_id
            enriched.append(item)
        return enriched

    def list_logs(self, *, limit: int = 150) -> list[dict[str, Any]]:
        items = self._read_json(LOGS_PATH)[: max(1, min(limit, 1000))]
        return self._enrich_log_session_ids(items)

    def summarize_logs(self) -> dict[str, Any]:
        items = self._read_json(LOGS_PATH)
        intents = Counter((item.get('intent') or 'unknown') for item in items)
        total = len(items)
        errors = sum(1 for item in items if bool(item.get('isError')))
        return {
            'total': total,
            'errors': errors,
            'topIntents': [
                {'intent': name, 'count': count}
                for name, count in intents.most_common(10)
            ],
        }

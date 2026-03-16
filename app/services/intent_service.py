from __future__ import annotations

import re
from datetime import date, timedelta


REGION_ALIAS = {
    "강남": ("서울", 1100000000),
    "역삼": ("서울", 1100000000),
    "삼성": ("서울", 1100000000),
    "서초": ("서울", 1100000000),
    "잠실": ("서울", 1100000000),
    "홍대": ("서울", 1100000000),
    "성수": ("서울", 1100000000),
    "마포": ("서울", 1100000000),
    "송파": ("서울", 1100000000),
    "강동": ("서울", 1100000000),
    "강북": ("서울", 1100000000),
    "강서": ("서울", 1100000000),
    "서울": ("서울", 1100000000),
    "판교": ("경기", 4100000000),
    "수원": ("경기", 4100000000),
    "성남": ("경기", 4100000000),
    "고양": ("경기", 4100000000),
    "용인": ("경기", 4100000000),
    "경기": ("경기", 4100000000),
    "인천": ("인천", 2800000000),
    "부산": ("부산", 2600000000),
    "해운대": ("부산", 2600000000),
    "대구": ("대구", 2700000000),
    "광주": ("광주", 2900000000),
    "대전": ("대전", 3000000000),
    "울산": ("울산", 3100000000),
    "세종": ("세종", 3611000000),
    "세종시": ("세종", 3611000000),
    "세종특별자치시": ("세종", 3611000000),
    "전주": ("전북", 5200000000),
    "전북": ("전북", 5200000000),
    "전남": ("전남", 4600000000),
    "강원": ("강원", 5100000000),
    "충북": ("충북", 4300000000),
    "충남": ("충남", 4400000000),
    "경북": ("경북", 4700000000),
    "경남": ("경남", 4800000000),
    "제주": ("제주", 5000000000),
    "제주시": ("제주", 5000000000),
    "서귀포": ("제주", 5000000000),
    "울릉도": ("경북", 4700000000),
}

FOLLOWUP_HINTS = {
    "환불": "refund_method",
    "취소": "refund_method",
    "문의": "system_inquiry",
    "로그인": "system_login",
    "결제": "system_payment",
    "주최자": "host_help",
    "부스": "system_booth",
    "관리자": "admin_contact_prompt",
}

GENERIC_KEYWORD_TOKENS = {
    "행사", "이벤트", "추천", "추천해줘", "알려줘", "찾아줘", "보여줘", "검색", "조회", "뭐", "뭐있어",
    "있어", "열리", "열리는", "개최", "하는", "근처", "주변", "인근", "가까운", "근방", "지역", "기준",
    "무료", "유료", "신청", "가능", "모집", "중", "이번", "주", "이번주", "주말", "이번달", "달", "오늘", "내일",
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "제주", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남",
}


class IntentService:
    def _last_text(self, history: list[dict] | None) -> str:
        items = history or []
        for item in reversed(items):
            text = str(item.get("text") or "").strip()
            if text:
                return text
        return ""

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", "", re.sub(r"[!?.,~]+", " ", text or "")).lower()

    def _contains_any(self, text: str, candidates: list[str]) -> bool:
        normalized = self._normalize(text)
        return any(self._normalize(candidate) in normalized for candidate in candidates)

    def detect(self, message: str, page_type: str | None = None, history: list[dict] | None = None) -> str:
        raw = (message or "").strip()
        normalized = self._normalize(raw)
        last_text = self._last_text(history)

        if raw.startswith("관리자 문의:"):
            return "admin_contact_submit"
        if self._contains_any(raw, ["관리자에게 문의", "관리자 문의하고 싶", "상담원 연결", "운영자 문의"]):
            return "admin_contact_prompt"
        if self._contains_any(raw, ["주최자는", "주최자 기능", "호스트는", "행사 등록은 어떻게", "주최할 수"]):
            return "host_help"
        if self._contains_any(raw, ["환불 규정", "환불 정책", "취소 규정", "환불 기준"]):
            return "refund_policy"
        if self._contains_any(raw, ["환불 어떻게", "환불 어디서", "취소 어떻게", "취소 어디서", "환불 방법"]):
            return "refund_method"
        if self._contains_any(raw, ["로그인이 안", "로그인 안", "비밀번호", "비번", "로그인 실패"]):
            return "system_login"
        if self._contains_any(raw, ["회원가입", "가입이 안", "가입 안"]):
            return "system_signup"
        if self._contains_any(raw, ["결제 실패", "결제가 안", "결제가 실패", "카드 결제"]):
            return "system_payment"
        if self._contains_any(raw, ["문의를 어떻게", "문의는 어디", "문의 남겨", "문의 작성"]):
            return "system_inquiry"
        if self._contains_any(raw, ["신고", "문제 행사", "스팸 행사"]):
            return "system_report"
        if self._contains_any(raw, ["부스 신청", "부스는 어떻게", "부스 모집"]):
            return "system_booth"
        if self._contains_any(raw, ["내 문의", "문의 내역", "작성 문의", "받은 문의"]):
            return "my_inquiry"
        if self._contains_any(raw, ["내 참여", "참여 행사", "참여 내역", "신청 내역", "결제한 행사", "참가한 행사"]):
            return "my_participation"
        if self._contains_any(raw, ["내 관심 행사", "찜한 행사", "위시리스트", "wishlist"]):
            return "my_wishlist"
        if self._contains_any(raw, ["마이페이지", "마이 페이지", "관심 행사"]):
            return "system_mypage"

        has_event_noun = any(token in normalized for token in ["행사", "이벤트", "전시", "축제", "컨퍼런스", "박람회", "공연"])
        has_search_verb = any(token in normalized for token in ["추천", "찾아", "알려", "보여", "뭐있", "조회", "검색"])
        has_region = self.extract_region(raw) is not None
        has_date_hint = any(token in normalized for token in ["이번주", "주말", "이번달", "오늘", "내일"])
        has_proximity = any(token in normalized for token in ["근처", "주변", "인근", "근방", "가까운", "쪽"])

        if (has_event_noun and (has_search_verb or has_date_hint or has_proximity or has_region)) or (
            page_type in {"map", "calendar", "board", "mypage"} and (has_region or has_date_hint)
        ):
            return "recommend"

        if self._contains_any(raw, ["안녕", "하이", "반가", "고마워", "감사", "도움말"]):
            return "smalltalk"

        if raw.endswith("어떻게 해?") or raw.endswith("어떻게 해") or raw.endswith("어디서 해?") or raw.endswith("어디서 해"):
            for hint, intent in FOLLOWUP_HINTS.items():
                if hint in last_text:
                    return intent

        return "chat"

    def extract_region(self, message: str, region_hint: str | None = None, location_keywords: list[str] | None = None):
        merged = " ".join(filter(None, [message or "", region_hint or "", " ".join(location_keywords or [])]))
        for alias, (name, region_id) in sorted(REGION_ALIAS.items(), key=lambda item: len(item[0]), reverse=True):
            if alias in merged:
                return {"alias": alias, "name": name, "regionId": region_id}
        return None

    def _strip_region_words(self, text: str) -> str:
        result = text
        for alias in sorted(REGION_ALIAS.keys(), key=len, reverse=True):
            result = result.replace(alias, " ")
        return result

    def extract_keyword(self, message: str) -> str | None:
        text = (message or "").strip()
        text = self._strip_region_words(text)
        text = re.sub(
            r"(추천해줘|추천해|알려줘|알려줘요|찾아줘|찾아줘요|보여줘|보여줘요|검색해줘|조회해줘|열리는|열리나|열려요|개최되는|개최하는|진행되는|진행하는|가볼만한|갈만한|위주로|기준으로|근처에서|근처|주변에서|주변|인근|근방|쪽에서|쪽|신청 가능한|신청가능한|모집중인|모집 중인|모집중|모집 중|이번 주말|이번주말|이번 주|이번주|주말|이번 달|이번달|오늘|내일|무료 행사|무료|유료|행사|이벤트)",
            " ",
            text,
        )
        text = re.sub(r"(에서|에|로|으로|쪽|근처|주변|인근)$", " ", text)
        text = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", text)
        tokens = [token for token in re.split(r"\s+", text) if token]
        filtered = [token for token in tokens if len(token) >= 2 and token not in GENERIC_KEYWORD_TOKENS and token not in {"에서", "으로", "근처에서", "주변에서", "대해", "관련"}]
        if not filtered:
            return None
        keyword = " ".join(filtered[:4]).strip()
        return keyword or None

    def _today(self) -> date:
        return date.today()

    def _week_range(self) -> tuple[date, date]:
        today = self._today()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end

    def _weekend_range(self) -> tuple[date, date]:
        today = self._today()
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        sunday = saturday + timedelta(days=1)
        return saturday, sunday

    def _month_range(self) -> tuple[date, date]:
        today = self._today()
        start = today.replace(day=1)
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        end = next_month - timedelta(days=1)
        return start, end

    def _date_range(self, text: str) -> dict | None:
        if "이번 주말" in text or "이번주말" in text or "주말" in text:
            start, end = self._weekend_range()
            return {"start": str(start), "end": str(end), "label": "이번 주말", "strict": True, "mode": "weekend"}
        if "이번 주" in text or "이번주" in text:
            start, end = self._week_range()
            return {"start": str(start), "end": str(end), "label": "이번 주", "strict": True, "mode": "this_week"}
        if "이번 달" in text or "이번달" in text:
            start, end = self._month_range()
            return {"start": str(start), "end": str(end), "label": "이번 달", "strict": False, "mode": "this_month"}
        if "오늘" in text:
            today = self._today()
            return {"start": str(today), "end": str(today), "label": "오늘", "strict": True, "mode": "today"}
        if "내일" in text:
            target = self._today() + timedelta(days=1)
            return {"start": str(target), "end": str(target), "label": "내일", "strict": True, "mode": "tomorrow"}
        return None

    def build_preferences(self, message: str, *, page_type: str | None = None, region_hint: str | None = None, location_keywords: list[str] | None = None, filters: dict | None = None) -> dict:
        text = (message or "").strip()
        filters = filters or {}
        prefer_free = any(x in text for x in ["무료", "공짜"])
        open_only = any(x in text for x in ["신청 가능", "모집중", "모집 중", "참여 모집"])
        if filters.get("applyOnly") is True:
            open_only = True
        return {
            "page_type": page_type,
            "region": self.extract_region(text, region_hint=region_hint, location_keywords=location_keywords),
            "keyword": self.extract_keyword(text),
            "open_only": open_only,
            "prefer_free": prefer_free,
            "date_range": self._date_range(text),
        }

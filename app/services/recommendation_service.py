from __future__ import annotations

from datetime import date
from typing import List, Tuple

from app.services.intent_service import IntentService
from app.services.spring_api_service import SpringApiService


class RecommendationService:
    def __init__(self) -> None:
        self.spring = SpringApiService()
        self.intent = IntentService()

    def _pick(self, *values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    def _format_region(self, event: dict) -> str:
        region = event.get("region")
        region_name = event.get("regionName")
        lot_number = event.get("lotNumberAdr")

        if isinstance(region, dict):
            parent = str(self._pick(region.get("parentName"), region.get("parentRegionName"), "") or "").strip()
            child = str(self._pick(region.get("regionName"), region.get("name"), "") or "").strip()
            if child.startswith(parent) and parent:
                return child
            return " ".join(part for part in [parent, child] if part).strip()

        if isinstance(region_name, str) and region_name.strip():
            return region_name.strip()
        if isinstance(region, str) and region.strip():
            return region.strip()
        if isinstance(lot_number, str) and lot_number.strip():
            return lot_number.strip()
        return ""

    def _normalize_card(self, event: dict) -> dict:
        event_id = self._pick(event.get("eventId"), event.get("id"), event.get("EVENT_ID"))
        title = self._pick(event.get("title"), event.get("eventTitle"), "추천 행사")
        description = self._pick(event.get("description"), event.get("eventDesc"), event.get("simpleExplain"), "")
        region = self._format_region(event)
        start_date = self._pick(event.get("startDate"), event.get("start_date"), "")
        end_date = self._pick(event.get("endDate"), event.get("end_date"), start_date)
        status = self._pick(event.get("eventStatus"), event.get("status"), "")
        thumbnail = self._pick(event.get("thumbnail"), event.get("thumbUrl"), event.get("imageUrl"), "")
        return {
            "eventId": int(event_id) if str(event_id).isdigit() else None,
            "title": str(title),
            "description": str(description or ""),
            "region": str(region or ""),
            "startDate": str(start_date or ""),
            "endDate": str(end_date or start_date or ""),
            "thumbnail": str(thumbnail or ""),
            "eventStatus": str(status or ""),
            "detailUrl": f"/events/{event_id}" if event_id else "",
            "applyUrl": f"/events/{event_id}/apply" if event_id and str(status) == "행사참여모집중" else "",
            "scoreReason": "",
            "raw": event,
        }

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except Exception:
            return None

    def _overlaps(self, card: dict, date_range: dict | None) -> bool:
        if not date_range:
            return True
        range_start = self._parse_date(date_range.get("start"))
        range_end = self._parse_date(date_range.get("end"))
        start = self._parse_date(card.get("startDate"))
        end = self._parse_date(card.get("endDate")) or start
        if not start:
            return False
        if not range_start or not range_end:
            return True
        return start <= range_end and (end or start) >= range_start

    def _match_region(self, region_text: str, region_name: str, alias: str | None) -> bool:
        text = (region_text or "").replace(" ", "")
        rn = (region_name or "").replace(" ", "")
        al = (alias or "").replace(" ", "")
        return bool((rn and rn in text) or (al and al in text))

    def _is_free(self, card: dict) -> bool:
        raw = card.get("raw") or {}
        price = self._pick(raw.get("price"), raw.get("payAmount"), raw.get("fee"), 0)
        try:
            return int(price or 0) <= 0
        except Exception:
            return False

    def _popularity(self, raw: dict) -> int:
        for key in ("viewCount", "views", "likeCount", "wishlistCount", "participantCount"):
            value = raw.get(key)
            try:
                return int(value or 0)
            except Exception:
                continue
        return 0

    def _score_card(self, card: dict, *, prefs: dict, user_context: dict) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []
        region = prefs.get("region")
        keyword = (prefs.get("keyword") or "").strip().lower()
        open_only = prefs.get("open_only")
        prefer_free = prefs.get("prefer_free")
        date_range = prefs.get("date_range")
        raw = card.get("raw") or {}
        title = str(card.get("title") or "").lower()
        desc = str(card.get("description") or "").lower()
        region_text = card.get("region") or ""
        status = card.get("eventStatus") or ""

        if status == "행사종료":
            return -999, ["종료 행사 제외"]

        if region and self._match_region(region_text, region.get("name", ""), region.get("alias")):
            score += 40
            reasons.append(f"{region.get('alias') or region.get('name')} 지역")

        if date_range and self._overlaps(card, date_range):
            score += 35
            reasons.append(date_range.get("label") or "일정 일치")

        if open_only and status == "행사참여모집중":
            score += 30
            reasons.append("지금 신청 가능")
        elif open_only:
            score -= 20

        if prefer_free and self._is_free(card):
            score += 12
            reasons.append("무료 행사")

        if keyword:
            kw_tokens = [token for token in keyword.split() if len(token) >= 2]
            matched = [token for token in kw_tokens if token in title or token in desc]
            if matched:
                score += 18 + (len(matched) * 3)
                reasons.append("키워드 일치")

        popularity = self._popularity(raw)
        if popularity > 0:
            score += min(15, popularity // 10)
            reasons.append("인기 행사")

        if card.get("eventId") in user_context.get("wishlist_event_ids", set()):
            score += 14
            reasons.append("관심 행사 기반")
        if card.get("eventId") in user_context.get("participation_event_ids", set()):
            score += 10
            reasons.append("참여 이력 기반")

        return score, reasons

    async def _search_with_fallbacks(self, *, keyword: str | None, region_id: int | None, open_only: bool, size: int) -> list[dict]:
        search_keywords = []
        if keyword:
            search_keywords.append(keyword)
        search_keywords.append(None)

        merged: list[dict] = []
        seen: set[str] = set()
        for current_keyword in search_keywords:
            try:
                items = await self.spring.search_events(
                    keyword=current_keyword,
                    region_id=region_id,
                    hide_closed=True,
                    event_status="행사참여모집중" if open_only else None,
                    size=size,
                )
            except Exception:
                items = []
            for item in items or []:
                key = str(self._pick(item.get("eventId"), item.get("id"), item.get("EVENT_ID"), item.get("title"), len(merged)))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
            if len(merged) >= size:
                break
        return merged

    async def _collect_candidates(self, *, prefs: dict, authorization: str | None) -> list[dict]:
        region = prefs.get("region")
        keyword = prefs.get("keyword")
        open_only = prefs.get("open_only")
        size = 80 if prefs.get("date_range") else 48

        if region:
            region_items = await self._search_with_fallbacks(
                keyword=keyword,
                region_id=region.get("regionId"),
                open_only=open_only,
                size=size,
            )
            if region_items:
                return region_items

        base = await self._search_with_fallbacks(
            keyword=keyword,
            region_id=None,
            open_only=open_only,
            size=size,
        )
        if base:
            return base
        try:
            return await self.spring.recommend_events(authorization=authorization)
        except Exception:
            return []

    async def _build_user_context(self, authorization: str | None) -> dict:
        if not authorization:
            return {"wishlist_event_ids": set(), "participation_event_ids": set()}
        try:
            wishlist = await self.spring.get_my_wishlist(authorization)
        except Exception:
            wishlist = []
        try:
            participations = await self.spring.get_my_participations(authorization)
        except Exception:
            participations = []
        return {
            "wishlist_event_ids": {item.get("eventId") for item in wishlist if item.get("eventId") is not None},
            "participation_event_ids": {item.get("eventId") for item in participations if item.get("eventId") is not None},
        }

    def _empty_answer(self, prefs: dict) -> str:
        if prefs.get("date_range"):
            return f"{prefs['date_range'].get('label') or '해당 기간'}에 진행되는 행사를 찾지 못했어요. 다른 지역이나 키워드로 다시 물어봐 주세요."
        if prefs.get("region"):
            return f"{prefs['region'].get('alias') or prefs['region'].get('name')} 기준으로 맞는 행사를 찾지 못했어요. 지역을 조금 넓혀서 다시 찾아볼까요?"
        return "조건에 맞는 행사를 아직 찾지 못했어요. 지역이나 일정 조건을 조금 바꿔서 다시 물어봐 주세요."

    async def recommend(
        self,
        *,
        message: str,
        authorization: str | None = None,
        page_type: str | None = None,
        region_hint: str | None = None,
        location_keywords: list[str] | None = None,
        filters: dict | None = None,
    ) -> Tuple[str, List[dict]]:
        import time

        start = time.perf_counter()

        prefs = self.intent.build_preferences(
            message,
            page_type=page_type,
            region_hint=region_hint,
            location_keywords=location_keywords,
            filters=filters,
        )
        prefs_t = time.perf_counter()

        user_context = await self._build_user_context(authorization)
        user_context_t = time.perf_counter()

        candidates = await self._collect_candidates(prefs=prefs, authorization=authorization)
        retrieval_t = time.perf_counter()

        cards = [self._normalize_card(item) for item in candidates or []]
        normalize_t = time.perf_counter()

        scored_cards = []
        strict_date = bool((prefs.get("date_range") or {}).get("strict"))
        explicit_region = prefs.get("region") is not None

        for card in cards:
            score, reasons = self._score_card(card, prefs=prefs, user_context=user_context)
            if score <= -999:
                continue
            if explicit_region and not self._match_region(
                card.get("region", ""),
                prefs["region"].get("name", ""),
                prefs["region"].get("alias"),
            ):
                continue
            if prefs.get("open_only") and card.get("eventStatus") != "행사참여모집중":
                continue
            if prefs.get("prefer_free") and not self._is_free(card):
                continue
            if prefs.get("date_range") and not self._overlaps(card, prefs.get("date_range")):
                continue
            card["scoreReason"] = ", ".join((reasons or ["조건 기반 추천"])[:3])
            scored_cards.append((score, card))

        score_t = time.perf_counter()

        if not scored_cards and not strict_date and not explicit_region:
            relaxed = [
                self._normalize_card(item)
                for item in await self.spring.search_events(
                    keyword=prefs.get("keyword"),
                    hide_closed=True,
                    size=36,
                )
            ]
            relaxed_t = time.perf_counter()

            for card in relaxed:
                if prefs.get("open_only") and card.get("eventStatus") != "행사참여모집중":
                    continue
                score, reasons = self._score_card(
                    card,
                    prefs={**prefs, "date_range": None},
                    user_context=user_context,
                )
                card["scoreReason"] = ", ".join((reasons or ["조건 완화 추천"])[:3])
                scored_cards.append((score, card))
            relaxed_score_t = time.perf_counter()
        else:
            relaxed_t = score_t
            relaxed_score_t = score_t

        unique = {}
        for score, card in sorted(scored_cards, key=lambda item: item[0], reverse=True):
            key = card.get("eventId") or card.get("title")
            if key in unique:
                continue
            card.pop("raw", None)
            unique[key] = card
            if len(unique) >= 3:   # 8 -> 3
                break

        final_cards = list(unique.values())
        post_t = time.perf_counter()

        print(
            f"[RECOMMEND TIMING] "
            f"prefs={prefs_t - start:.3f}s "
            f"user={user_context_t - prefs_t:.3f}s "
            f"retrieval={retrieval_t - user_context_t:.3f}s "
            f"normalize={normalize_t - retrieval_t:.3f}s "
            f"score={score_t - normalize_t:.3f}s "
            f"relaxed_fetch={relaxed_t - score_t:.3f}s "
            f"relaxed_score={relaxed_score_t - relaxed_t:.3f}s "
            f"gemini=0.000s "
            f"post={post_t - relaxed_score_t:.3f}s "
            f"total={post_t - start:.3f}s"
        )

        if not final_cards:
            return self._empty_answer(prefs), []

        reason_parts = []
        if prefs.get("region"):
            reason_parts.append(f"{prefs['region'].get('alias') or prefs['region'].get('name')} 기준")
        if prefs.get("date_range"):
            reason_parts.append(prefs["date_range"].get("label") or "일정 반영")
        if prefs.get("open_only"):
            reason_parts.append("신청 가능 우선")
        if prefs.get("prefer_free"):
            reason_parts.append("무료 우선")

        lead = " / ".join(reason_parts) if reason_parts else "현재 조건 기준"
        return f"{lead}으로 조건에 맞는 행사들을 골라봤어요.", final_cards

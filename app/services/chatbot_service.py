from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.schemas.chat_schema import ChatResponse
from app.services.action_service import ActionService
from app.services.answer_composer_service import AnswerComposerService
from app.services.chat_log_service import ChatLogService
from app.services.gemini_service import GeminiService
from app.services.intent_service import IntentService
from app.services.recommendation_service import RecommendationService
from app.services.retrieval_service import RetrievalService


@dataclass
class RouteDecision:
    route_type: str
    intent: str
    action_name: str | None = None
    classifier: str | None = None


class ChatbotService:
    def __init__(self) -> None:
        self.intent = IntentService()
        self.retrieval = RetrievalService()
        self.recommender = RecommendationService()
        self.action_service = ActionService()
        self.answer_composer = AnswerComposerService()
        self.gemini = GeminiService()
        self.logs = ChatLogService()

    def _log(
        self,
        *,
        started_at: float,
        session_id: str | None,
        page_type: str | None,
        intent: str | None,
        route_type: str,
        message: str,
        answer: str,
        cards: list | None,
        sources: list | None,
        status_code: int = 200,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        self.logs.log_event(
            session_id=session_id,
            client_key=None,
            page_type=page_type,
            intent=intent,
            status_code=status_code,
            latency_ms=latency_ms,
            message=message,
            answer_preview=answer,
            card_count=len(cards or []),
            source_count=len(sources or []),
            metadata={"routeType": route_type, **(metadata or {})},
        )

    def _heuristic_route(
        self,
        raw_message: str,
        *,
        page_type: str | None,
        history: list[dict] | None,
        region_hint: str | None,
        location_keywords: list[str] | None,
    ) -> RouteDecision:
        text = (raw_message or "").strip()
        lowered = text.lower()
        if lowered.startswith("관리자 문의:") or lowered.startswith("관리자문의:"):
            return RouteDecision(route_type="action", intent="admin_contact", action_name="submit_admin_contact", classifier="rule")
        if "관리자" in text and "문의" in text:
            return RouteDecision(route_type="action", intent="admin_contact_help", action_name="admin_contact_help", classifier="rule")
        if "결제" in text and any(token in text for token in ["상태", "내역", "확인", "보여"]):
            return RouteDecision(route_type="action", intent="payment", action_name="my_payment_statuses", classifier="rule")
        if "환불" in text and any(token in text for token in ["상태", "처리", "내역", "확인", "보여"]):
            return RouteDecision(route_type="action", intent="refund", action_name="my_refund_statuses", classifier="rule")
        if "부스" in text and any(token in text for token in ["상태", "신청", "내역", "확인", "보여"]):
            return RouteDecision(route_type="action", intent="booth", action_name="my_booth_statuses", classifier="rule")
        if "내 문의" in text or ("문의 내역" in text and "내" in text) or ("ai 문의" in text and "내" in text):
            return RouteDecision(route_type="action", intent="my_inquiry", action_name="my_inquiries", classifier="rule")
        if ("내 참여" in text) or ("참여 행사" in text and "내" in text) or ("신청 내역" in text):
            return RouteDecision(route_type="action", intent="my_participation", action_name="my_participations", classifier="rule")
        if ("관심 행사" in text) or ("찜" in text and any(token in text for token in ["목록", "내역", "보여", "확인"])):
            return RouteDecision(route_type="action", intent="my_wishlist", action_name="my_wishlist", classifier="rule")
        if ("내" in text and "상태" in text) or ("내" in text and "현황" in text) or ("신청" in text and "상태" in text):
            return RouteDecision(route_type="action", intent="my_status", action_name="my_status_summary", classifier="rule")
        if self.intent.looks_like_event_request(text, page_type=page_type, region_hint=region_hint, location_keywords=location_keywords):
            return RouteDecision(route_type="recommendation", intent="event_search", classifier="heuristic")

        hint_intent = self.intent.detect(text, page_type=page_type, history=history)
        if hint_intent in {"recommend"}:
            return RouteDecision(route_type="recommendation", intent="event_search", classifier="intent")
        if hint_intent in {"my_inquiry"}:
            return RouteDecision(route_type="action", intent="my_inquiry", action_name="my_inquiries", classifier="intent")
        if hint_intent in {"my_participation"}:
            return RouteDecision(route_type="action", intent="my_participation", action_name="my_participations", classifier="intent")
        if hint_intent in {"my_wishlist"}:
            return RouteDecision(route_type="action", intent="my_wishlist", action_name="my_wishlist", classifier="intent")
        if hint_intent in {"admin_contact_prompt"}:
            return RouteDecision(route_type="action", intent="admin_contact_help", action_name="admin_contact_help", classifier="intent")
        if hint_intent in {"refund_policy", "refund_method", "system_login", "system_signup", "system_payment", "system_inquiry", "system_report", "system_booth", "system_mypage", "host_help"}:
            return RouteDecision(route_type="retrieval", intent="policy", classifier="intent")
        return RouteDecision(route_type="retrieval", intent="general", classifier="fallback")

    async def _decide_route(
        self,
        raw_message: str,
        *,
        page_type: str | None,
        history: list[dict] | None,
        region_hint: str | None,
        location_keywords: list[str] | None,
    ) -> RouteDecision:
        heuristic = self._heuristic_route(
            raw_message,
            page_type=page_type,
            history=history,
            region_hint=region_hint,
            location_keywords=location_keywords,
        )
        if heuristic.route_type in {"action", "recommendation"}:
            return heuristic

        semantic = await self.gemini.classify_route(
            user_message=raw_message,
            page_type=page_type,
            history=history,
        )
        if semantic == "event_search":
            return RouteDecision(route_type="recommendation", intent="event_search", classifier="gemini")
        mapping = {
            "my_status": ("action", "my_status", "my_status_summary"),
            "my_inquiries": ("action", "my_inquiry", "my_inquiries"),
            "my_participations": ("action", "my_participation", "my_participations"),
            "my_wishlist": ("action", "my_wishlist", "my_wishlist"),
            "payment": ("action", "payment", "my_payment_statuses"),
            "refund": ("action", "refund", "my_refund_statuses"),
            "booth": ("action", "booth", "my_booth_statuses"),
            "admin_contact_help": ("action", "admin_contact_help", "admin_contact_help"),
            "admin_contact_submit": ("action", "admin_contact", "submit_admin_contact"),
            "policy": ("retrieval", "policy", None),
            "general": ("retrieval", "general", None),
        }
        if semantic in mapping:
            route_type, intent, action_name = mapping[semantic]
            return RouteDecision(route_type=route_type, intent=intent, action_name=action_name, classifier="gemini")
        return heuristic

    async def chat(
        self,
        *,
        message: str,
        authorization: str | None = None,
        history: list[dict] | None = None,
        session_id: str | None = None,
        page_type: str | None = None,
        region_hint: str | None = None,
        location_keywords: list[str] | None = None,
        filters: dict | None = None,
    ) -> ChatResponse:
        started_at = time.perf_counter()
        debug_start = time.perf_counter()
        raw_message = (message or "").strip()

        try:
            route = await self._decide_route(
                raw_message,
                page_type=page_type,
                history=history,
                region_hint=region_hint,
                location_keywords=location_keywords,
            )
            route_t = time.perf_counter()

            if route.route_type == "recommendation":
                answer, cards = await self.recommender.recommend(
                    message=raw_message,
                    authorization=authorization,
                    page_type=page_type,
                    region_hint=region_hint,
                    location_keywords=location_keywords,
                    filters=filters,
                )
                recommend_t = time.perf_counter()

                reasons = [card.get("scoreReason") for card in cards[:3] if isinstance(card, dict) and card.get("scoreReason")]
                next_actions = []
                if cards:
                    next_actions = [
                        {"label": "상세 페이지 보기", "actionType": "navigate", "value": cards[0].get("detailUrl") or "", "variant": "primary"},
                        {"label": "무료 행사만 추천", "actionType": "prompt", "value": "무료 행사만 추천해줘", "variant": "secondary"},
                    ]
                post_t = time.perf_counter()

                print(
                    f"[CHAT TIMING] route={route_t - debug_start:.3f}s "
                    f"recommend={recommend_t - route_t:.3f}s "
                    f"post={post_t - recommend_t:.3f}s "
                    f"total={post_t - debug_start:.3f}s"
                )

                self._log(
                    started_at=started_at,
                    session_id=session_id,
                    page_type=page_type,
                    intent=route.intent,
                    route_type="recommendation",
                    message=raw_message,
                    answer=answer,
                    cards=cards,
                    sources=[],
                    metadata={"recommendationReasons": reasons, "classifier": route.classifier},
                )
                return ChatResponse(
                    answer=answer,
                    cards=cards,
                    sources=[],
                    intent=route.intent,
                    routeType="recommendation",
                    recommendationReasons=reasons,
                    nextActions=next_actions,
                )

            if route.route_type == "action" and route.action_name:
                action_result = await self.action_service.dispatch(
                    action_name=route.action_name,
                    raw_message=raw_message,
                    authorization=authorization,
                    session_id=session_id,
                    page_type=page_type,
                )
                action_t = time.perf_counter()
                post_t = time.perf_counter()

                print(
                    f"[CHAT TIMING] route={route_t - debug_start:.3f}s "
                    f"action={action_t - route_t:.3f}s "
                    f"post={post_t - action_t:.3f}s "
                    f"total={post_t - debug_start:.3f}s"
                )

                self._log(
                    started_at=started_at,
                    session_id=session_id,
                    page_type=page_type,
                    intent=route.intent,
                    route_type="action",
                    message=raw_message,
                    answer=action_result.answer,
                    cards=action_result.cards,
                    sources=[],
                    status_code=action_result.status_code,
                    metadata={**(action_result.metadata or {}), "classifier": route.classifier},
                )
                return ChatResponse(
                    answer=action_result.answer,
                    cards=action_result.cards,
                    sources=[],
                    intent=route.intent,
                    routeType="action",
                    recommendationReasons=action_result.recommendation_reasons,
                    nextActions=action_result.next_actions,
                )

            retrieval = await self.retrieval.retrieve(
                raw_message,
                intent=route.intent if route.intent != "general" else None,
                limit=5,
            )
            retrieval_t = time.perf_counter()

            composed = await self.answer_composer.compose_explanation(
                user_message=raw_message,
                history=history,
                intent=route.intent,
                retrieval=retrieval,
            )
            gemini_t = time.perf_counter()
            post_t = time.perf_counter()

            print(
                f"[CHAT TIMING] route={route_t - debug_start:.3f}s "
                f"retrieval={retrieval_t - route_t:.3f}s "
                f"gemini={gemini_t - retrieval_t:.3f}s "
                f"post={post_t - gemini_t:.3f}s "
                f"total={post_t - debug_start:.3f}s"
            )

            self._log(
                started_at=started_at,
                session_id=session_id,
                page_type=page_type,
                intent=route.intent,
                route_type=composed.route_type,
                message=raw_message,
                answer=composed.answer,
                cards=[],
                sources=composed.sources,
                metadata={**(composed.metadata or {}), "classifier": route.classifier},
            )
            return ChatResponse(
                answer=composed.answer,
                cards=[],
                sources=composed.sources,
                intent=route.intent,
                routeType=composed.route_type,
                recommendationReasons=composed.recommendation_reasons or [],
                nextActions=composed.next_actions or [],
            )
        except Exception as e:
            print("[CHATBOT ERROR]", repr(e))
            answer = "지금은 답변을 처리하는 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요."
            self._log(
                started_at=started_at,
                session_id=session_id,
                page_type=page_type,
                intent="error",
                route_type="error",
                message=raw_message,
                answer=answer,
                cards=[],
                sources=[],
                status_code=500,
                metadata={"error": repr(e)},
            )
            return ChatResponse(
                answer=answer,
                cards=[],
                sources=[],
                recommendationReasons=[],
                nextActions=[],
                intent="error",
                routeType="error",
            )
            
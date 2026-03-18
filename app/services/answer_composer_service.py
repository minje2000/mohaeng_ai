from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.chat_schema import ChatNextAction, ChatSource
from app.services.gemini_service import GeminiService
from app.services.retrieval_service import RetrievalResult


@dataclass
class ComposedAnswer:
    answer: str
    sources: list[ChatSource]
    route_type: str
    metadata: dict[str, Any] | None = None
    next_actions: list[ChatNextAction] | None = None
    recommendation_reasons: list[str] | None = None


class AnswerComposerService:
    def __init__(self) -> None:
        self.gemini = GeminiService()

    def _to_chat_sources(self, retrieval: RetrievalResult) -> list[ChatSource]:
        return [
            ChatSource(type=source.type, title=source.title, snippet=source.snippet)
            for source in retrieval.sources or []
        ]

    def _build_context_block(self, retrieval: RetrievalResult) -> str:
        if retrieval.answer_hint.strip():
            return retrieval.answer_hint.strip()
        parts: list[str] = []
        for index, source in enumerate(retrieval.sources[:5], start=1):
            parts.append(f"[참고 {index}] {source.title}\n{source.snippet}")
        return "\n\n".join(parts).strip()

    def _fallback_answer(self, *, sources: list[ChatSource]) -> str:
        if sources:
            titles = ", ".join(dict.fromkeys(source.title for source in sources[:3]))
            return f"관련 안내는 찾았지만 지금은 답변을 자연스럽게 정리하지 못했어요. 우선 참고 출처는 {titles}예요."
        return "지금은 확인 가능한 안내 문서를 찾지 못했어요. 질문을 조금 더 구체적으로 말씀해 주세요."

    def _append_next_step(self, *, answer: str, intent: str | None, sources: list[ChatSource]) -> str:
        text = (answer or "").strip()
        if not text:
            return text
        followup = None
        if intent in {"admin_contact", "admin_contact_help"}:
            followup = "필요하면 '관리자 문의: 내용' 형식으로 바로 남겨 주세요."
        elif intent in {"policy", "howto", "refund", "payment", "booth", "inquiry"} and sources:
            followup = "답변 아래 참고 출처와 다음 행동 버튼도 함께 확인해 주세요."
        if not followup or followup in text:
            return text
        return f"{text}\n\n{followup}".strip()

    def _next_actions_by_intent(self, intent: str | None) -> list[ChatNextAction]:
        mapping = {
            "policy": [
                ChatNextAction(label="환불 규정", actionType="prompt", value="환불 규정 알려줘", variant="secondary"),
                ChatNextAction(label="결제 상태", actionType="prompt", value="내 결제 상태 보여줘", variant="secondary"),
            ],
            "payment": [
                ChatNextAction(label="내 결제 상태", actionType="prompt", value="내 결제 상태 보여줘", variant="primary"),
                ChatNextAction(label="환불 처리 상태", actionType="prompt", value="내 환불 상태 알려줘", variant="secondary"),
            ],
            "refund": [
                ChatNextAction(label="내 환불 상태", actionType="prompt", value="내 환불 상태 알려줘", variant="primary"),
                ChatNextAction(label="관리자 문의", actionType="prompt", value="관리자 문의: 환불 상태 문의가 있어요", variant="secondary"),
            ],
            "booth": [
                ChatNextAction(label="내 부스 상태", actionType="prompt", value="내 부스 신청 상태 보여줘", variant="primary"),
                ChatNextAction(label="부스 신청 방법", actionType="prompt", value="부스 신청 방법 알려줘", variant="secondary"),
            ],
            "search_help": [
                ChatNextAction(label="행사 찾기", actionType="prompt", value="지금 신청 가능한 행사 찾아줘", variant="primary"),
                ChatNextAction(label="이번 주말 추천", actionType="prompt", value="이번 주말 행사 추천해줘", variant="secondary"),
            ],
        }
        return mapping.get(intent or "", [
            ChatNextAction(label="행사 찾기", actionType="prompt", value="지금 신청 가능한 행사 찾아줘", variant="secondary")
        ])

    async def compose_explanation(
        self,
        *,
        user_message: str,
        history: list[dict] | None,
        intent: str | None,
        retrieval: RetrievalResult,
    ) -> ComposedAnswer:
        sources = self._to_chat_sources(retrieval)
        context = self._build_context_block(retrieval)
        if not context:
            return ComposedAnswer(
                answer=self._fallback_answer(sources=sources),
                sources=sources,
                route_type="retrieval_fallback",
                metadata={"usedGemini": False, "sourceCount": len(sources)},
                next_actions=self._next_actions_by_intent(intent),
                recommendation_reasons=[],
            )
        generated = await self.gemini.generate(history or [], user_message, context=context)
        answer = (generated or "").strip() or self._fallback_answer(sources=sources)
        answer = self._append_next_step(answer=answer, intent=intent, sources=sources)
        return ComposedAnswer(
            answer=answer,
            sources=sources,
            route_type="retrieval",
            metadata={"usedGemini": True, "sourceCount": len(sources)},
            next_actions=self._next_actions_by_intent(intent),
            recommendation_reasons=[f"{source.title} 문서 기반" for source in sources[:3]],
        )

    async def compose_general_chat(
        self,
        *,
        user_message: str,
        history: list[dict] | None,
        retrieval: RetrievalResult,
    ) -> ComposedAnswer:
        sources = self._to_chat_sources(retrieval)
        context = self._build_context_block(retrieval)
        generated = await self.gemini.generate(history or [], user_message, context=context)
        answer = (generated or "").strip() or self._fallback_answer(sources=sources)
        answer = self._append_next_step(answer=answer, intent=None, sources=sources)
        return ComposedAnswer(
            answer=answer,
            sources=sources,
            route_type="fallback",
            metadata={"usedGemini": True, "sourceCount": len(sources)},
            next_actions=[ChatNextAction(label="행사 추천", actionType="prompt", value="행사 추천해줘", variant="secondary")],
            recommendation_reasons=[],
        )

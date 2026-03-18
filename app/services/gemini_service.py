from __future__ import annotations

import httpx
from app.core.config import settings


class GeminiService:
    def __init__(self) -> None:
        self.model = settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def _call(self, parts: list[dict]) -> str:
        if not settings.GEMINI_API_KEY:
            return ""
        payload = {"contents": [{"parts": parts}]}
        try:
            async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
                res = await client.post(
                    self.url,
                    headers={
                        "x-goog-api-key": settings.GEMINI_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            if res.status_code >= 400:
                print("[Gemini ERROR]", res.status_code, res.text)
                return ""
            data = res.json()
            return (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
        except Exception as e:
            print("[Gemini EXCEPTION]", repr(e))
            return ""

    async def generate(self, history: list[dict], user_message: str, context: str = "") -> str:
        if not settings.GEMINI_API_KEY:
            return "안녕하세요. MOHAENG AI 챗봇입니다. Gemini API 키가 아직 설정되지 않았어요."

        system_prompt = (
            "너는 행사 플랫폼 MOHAENG의 실서비스형 AI 챗봇이다.\n"
            "항상 한국어로 답하고, 과장 없이 짧고 명확하게 답한다.\n"
            "반드시 제공된 참고 컨텍스트를 우선 근거로 사용한다.\n"
            "컨텍스트에 없는 사실을 지어내지 말고, 불확실하면 모른다고 말한다.\n"
            "답변 방식은 다음 원칙을 따른다.\n"
            "1) 먼저 핵심 답을 2~4문장 안에 말한다.\n"
            "2) 서비스 정책, 사용 방법, 마이페이지, 문의, 환불, 부스, 신고 질문은 컨텍스트 중심으로 설명한다.\n"
            "3) 개인 데이터가 필요한 질문은 로그인 필요 여부를 분명히 말한다.\n"
            "4) 필요하면 마지막에 다음 행동 1개만 제안한다.\n"
            "5) 근거가 약하면 단정하지 않는다."
        )

        parts = [{"text": f"[시스템 지침]\n{system_prompt}\n\n[참고 컨텍스트]\n{context or '없음'}"}]
        for item in history[-6:]:
            role = item.get("role", "user")
            text = (item.get("text") or "").strip()
            if not text:
                continue
            speaker = "사용자" if role == "user" else "상담사"
            parts.append({"text": f"{speaker}: {text}"})
        parts.append({"text": f"사용자: {user_message}"})

        generated = await self._call(parts)
        return generated or "지금은 자연 대화 응답을 생성하지 못했어요. 잠시 후 다시 시도해 주세요."

    async def classify_route(self, *, user_message: str, page_type: str | None = None, history: list[dict] | None = None) -> str:
        if not settings.GEMINI_API_KEY:
            return ""
        examples = (
            "분류 라벨은 다음 중 하나만 사용한다:\n"
            "- event_search: 행사 추천, 행사 찾기, 행사 보여주기, 뭐 있어/갈만한 거/주변 행사 등 탐색 요청\n"
            "- my_status: 내 상태 요약, 내 진행 상황, 내 신청/문의 현황\n"
            "- my_inquiries: 내 문의 내역, 문의 확인\n"
            "- my_participations: 내 참여 행사, 신청 내역\n"
            "- my_wishlist: 관심 행사, 찜 목록\n"
            "- payment: 내 결제 상태, 결제 내역\n"
            "- refund: 내 환불 상태, 환불 처리 내역\n"
            "- booth: 내 부스 신청 상태\n"
            "- admin_contact_help: 관리자 문의 방법 문의\n"
            "- admin_contact_submit: '관리자 문의:'로 시작하는 실제 접수\n"
            "- policy: 환불 규정, 결제 방법, 문의 방법, 마이페이지, 부스, 신고, 주최자 기능 같은 정책/가이드 질문\n"
            "- general: 위에 해당하지 않는 일반 대화\n\n"
            "예시:\n"
            "'강남 근처 행사 알려줘' -> event_search\n"
            "'홍대 주변 행사 찾아줘' -> event_search\n"
            "'이번 주말 뭐 있어?' -> event_search\n"
            "'내 문의 내역 보여줘' -> my_inquiries\n"
            "'내 결제 상태 알려줘' -> payment\n"
            "'환불 규정 뭐야?' -> policy\n"
            "'관리자 문의: 챗봇이 이상해요' -> admin_contact_submit\n"
            "반드시 라벨 하나만 출력한다. 다른 설명은 금지한다."
        )
        parts = [{"text": f"[분류 지침]\n{examples}\n[페이지]\n{page_type or '없음'}"}]
        for item in (history or [])[-4:]:
            role = item.get("role", "user")
            text = (item.get("text") or "").strip()
            if text:
                speaker = "사용자" if role == "user" else "상담사"
                parts.append({"text": f"{speaker}: {text}"})
        parts.append({"text": f"사용자: {user_message}"})
        label = (await self._call(parts)).strip().lower()
        allowed = {
            "event_search", "my_status", "my_inquiries", "my_participations", "my_wishlist",
            "payment", "refund", "booth", "admin_contact_help", "admin_contact_submit", "policy", "general"
        }
        return label if label in allowed else ""

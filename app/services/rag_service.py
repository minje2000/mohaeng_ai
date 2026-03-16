from __future__ import annotations

from dataclasses import dataclass

from app.services.spring_api_service import SpringApiService


@dataclass
class RagMatch:
    answer: str
    sources: list[dict]


class RagService:
    REFUND_POLICY_TEXT = (
        "환불 규정 안내입니다.\n\n"
        "- 행사 시작 7일 전 취소: 전액 환불\n"
        "- 행사 시작 3~6일 전 취소: 50% 환불\n"
        "- 행사 시작 2일 전 ~ 당일 취소: 환불 불가\n"
        "- 주최자 사정으로 취소되거나 반려된 경우: 전액 환불\n"
        "- 실제 결제/환불 처리 시점은 PG사 또는 결제 수단 처리 일정에 따라 다를 수 있습니다."
    )

    INTENT_GUIDES = {
        "refund_method": (
            "환불은 마이페이지 → 참여 행사에서 신청 취소로 진행할 수 있어요.\n"
            "취소 시점에 따라 환불 금액이 달라져요. 환불 규정이 궁금하면 '환불 규정 알려줘'라고 말씀해 주세요.",
            "환불 방법 안내",
        ),
        "refund_policy": (REFUND_POLICY_TEXT, "기본 환불 정책"),
        "system_login": (
            "이메일과 비밀번호를 다시 확인해 주세요. 계속 실패하면 비밀번호 찾기를 이용하고, 동일한 문제가 반복되면 문의를 남겨 주세요.",
            "로그인 문제 안내",
        ),
        "system_signup": (
            "회원가입이 되지 않으면 이메일 중복 여부와 비밀번호 조건을 먼저 확인해 주세요. 입력이 모두 맞는데도 진행되지 않으면 문의를 남겨 주세요.",
            "회원가입 안내",
        ),
        "system_payment": (
            "결제가 실패하면 카드 한도, 결제 정보, 브라우저 새로고침 여부를 먼저 확인해 주세요. 계속 실패하면 같은 행사에 다시 시도하거나 문의를 남겨 주세요.",
            "결제 문제 안내",
        ),
        "system_inquiry": (
            "행사 상세 페이지에서 문의를 남길 수 있고, 마이페이지에서 작성 문의와 받은 문의를 확인할 수 있어요.",
            "문의 작성 안내",
        ),
        "system_mypage": (
            "마이페이지에서는 관심 행사, 참여 행사, 문의 내역, 리뷰 작성 내역 같은 내 활동을 확인할 수 있어요.",
            "마이페이지 안내",
        ),
        "system_booth": (
            "부스 신청은 부스 모집 중인 행사 상세에서 진행할 수 있어요. 신청 후에는 마이페이지에서 상태를 확인할 수 있어요.",
            "부스 신청 안내",
        ),
        "system_report": (
            "문제가 있는 행사나 이용자 행동은 신고 기능이나 문의를 통해 알려 주세요. 확인이 필요한 내용은 운영자가 검토해요.",
            "신고 안내",
        ),
        "host_help": (
            "주최자는 행사를 등록하고 수정할 수 있고, 참가 신청 현황과 문의를 관리할 수 있어요. 부스 모집 행사라면 부스 신청 현황도 확인할 수 있어요.",
            "주최자 기능 안내",
        ),
        "admin_contact": (
            "관리자에게 문의를 남기려면 '관리자 문의: 내용' 형식으로 보내 주세요. 예시: 관리자 문의: 결제 오류가 반복돼요",
            "관리자 문의 안내",
        ),
        "admin_contact_prompt": (
            "관리자에게 문의를 남기려면 '관리자 문의: 내용' 형식으로 보내 주세요. 예시: 관리자 문의: 결제 오류가 반복돼요",
            "관리자 문의 안내",
        ),
    }

    DEFAULT_FAQ = [
        {
            "title": "행사 신청 안내",
            "question": "행사는 어떻게 신청하나요?",
            "answer": "행사 상세 페이지에서 행사 상태가 '행사참여모집중'일 때 신청을 진행할 수 있어요.",
            "enabled": True,
        },
        {
            "title": "문의 확인 안내",
            "question": "문의 내역은 어디서 보나요?",
            "answer": "행사 상세 페이지에서 문의를 남길 수 있고, 마이페이지에서 작성 문의와 받은 문의를 확인할 수 있어요.",
            "enabled": True,
        },
        {
            "title": "관심 행사 안내",
            "question": "관심 행사 목록은 어디서 확인하나요?",
            "answer": "관심 행사는 찜 기능으로 저장할 수 있고, 마이페이지에서 다시 볼 수 있어요.",
            "enabled": True,
        },
        {
            "title": "주최자 기능 안내",
            "question": "주최자는 무엇을 할 수 있나요?",
            "answer": "주최자는 행사를 등록하고 관리할 수 있으며, 참가자 문의와 신청 현황도 확인할 수 있어요.",
            "enabled": True,
        },
    ]

    def __init__(self) -> None:
        self.spring = SpringApiService()

    def answer_for_intent(self, intent: str) -> RagMatch | None:
        guide = self.INTENT_GUIDES.get(intent)
        if not guide:
            return None
        answer, title = guide
        return RagMatch(
            answer=answer,
            sources=[{"type": "guide", "title": title, "snippet": title}],
        )

    async def answer_with_sources(self, message: str) -> RagMatch | None:
        text = (message or "").strip()
        lowered = text.lower()

        faq_items = await self.spring.get_public_faqs()
        candidates = [item for item in (faq_items or self.DEFAULT_FAQ) if item.get("enabled", True)]
        best: tuple[int, dict] | None = None

        for item in candidates:
            haystack = " ".join(
                [
                    str(item.get("title") or ""),
                    str(item.get("question") or ""),
                    str(item.get("answer") or ""),
                    " ".join(item.get("keywords") or []),
                ]
            ).lower()
            score = 0
            for token in lowered.split():
                if len(token) >= 2 and token in haystack:
                    score += 1
            if score > 0 and (best is None or score > best[0]):
                best = (score, item)

        if not best:
            return None

        faq = best[1]
        return RagMatch(
            answer=str(faq.get("answer") or ""),
            sources=[
                {
                    "type": "faq",
                    "title": str(faq.get("title") or faq.get("question") or "운영 FAQ"),
                    "snippet": str(faq.get("question") or ""),
                }
            ],
        )

    async def answer(self, message: str, *, intent: str | None = None) -> str | None:
        if intent:
            matched_intent = self.answer_for_intent(intent)
            if matched_intent and matched_intent.answer:
                return matched_intent.answer
        matched_faq = await self.answer_with_sources(message)
        if matched_faq and matched_faq.answer:
            return matched_faq.answer
        return None

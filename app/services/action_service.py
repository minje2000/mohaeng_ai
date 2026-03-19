from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas.chat_schema import ChatCard, ChatNextAction
from app.services.admin_support_service import AdminSupportService
from app.services.spring_api_service import SpringApiService


@dataclass
class ActionExecutionResult:
    answer: str
    cards: list[ChatCard] = field(default_factory=list)
    status_code: int = 200
    action_name: str | None = None
    metadata: dict[str, Any] | None = None
    recommendation_reasons: list[str] = field(default_factory=list)
    next_actions: list[ChatNextAction] = field(default_factory=list)


class ActionService:
    def __init__(self) -> None:
        self.spring = SpringApiService()
        self.admin_support = AdminSupportService()

    async def dispatch(
        self,
        *,
        action_name: str,
        raw_message: str,
        authorization: str | None,
        session_id: str | None,
        page_type: str | None = None,
    ) -> ActionExecutionResult:
        if action_name == "search_events":
            return await self.search_events(raw_message=raw_message)
        if action_name == "my_inquiries":
            return await self.get_my_inquiries(authorization=authorization)
        if action_name == "my_participations":
            return await self.get_my_participations(authorization=authorization)
        if action_name == "my_wishlist":
            return await self.get_my_wishlist(authorization=authorization)
        if action_name == "my_payment_statuses":
            return await self.get_my_payment_statuses(authorization=authorization)
        if action_name == "my_refund_statuses":
            return await self.get_my_refund_statuses(authorization=authorization)
        if action_name == "my_booth_statuses":
            return await self.get_my_booth_statuses(authorization=authorization)
        if action_name == "my_status_summary":
            return await self.get_my_status_summary(authorization=authorization)
        if action_name == "admin_contact_help":
            return self.get_admin_contact_help(raw_message=raw_message, authorization=authorization)
        if action_name == "submit_admin_contact":
            return await self.submit_admin_contact(raw_message=raw_message, authorization=authorization, session_id=session_id)
        return ActionExecutionResult(
            answer="처리 가능한 액션을 찾지 못했어요. 질문을 조금만 다르게 말씀해 주세요.",
            status_code=400,
            action_name="unknown_action",
            metadata={"pageType": page_type},
        )

    def _default_next_actions(self) -> list[ChatNextAction]:
        return [
            ChatNextAction(label="행사 찾기", actionType="prompt", value="지금 신청 가능한 행사 찾아줘", variant="secondary"),
            ChatNextAction(label="환불 규정 보기", actionType="prompt", value="환불 규정 알려줘", variant="secondary"),
        ]

    def _require_login_message(self, label: str) -> ActionExecutionResult:
        return ActionExecutionResult(
            answer=f"{label} 확인하려면 로그인이 필요해요. 로그인 후 다시 말씀해 주세요.",
            status_code=401,
            action_name="requires_login",
            metadata={"requiresAuth": True},
            next_actions=[ChatNextAction(label="로그인하기", actionType="navigate", value="/login", variant="primary")],
        )

    def _admin_contact_prompt(self) -> str:
        return (
            "관리자에게 전달할 내용을 아래 형식으로 보내주세요.\n\n"
            "관리자 문의: 문의 내용\n\n"
            "예) 관리자 문의: 결제가 됐는데 신청 내역이 안 보여요"
        )

    def _login_issue_email_guide(self) -> str:
        return (
            "로그인 자체가 되지 않으면 챗봇에서 관리자 문의를 접수할 수 없어요. "
            "이 경우 관리자 이메일 mohaeng8826@gmail.com 으로 상황을 보내 주세요."
        )

    @staticmethod
    def _safe_text(*values: Any, default: str = "") -> str:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return default

    def _build_event_card(self, item: dict[str, Any], *, default_title: str) -> ChatCard:
        raw_event_id = item.get("eventId") or item.get("id")
        event_id = None
        if raw_event_id is not None:
            try:
                event_id = int(raw_event_id)
            except (TypeError, ValueError):
                event_id = None
        return ChatCard(
            eventId=event_id,
            title=self._safe_text(item.get("eventTitle"), item.get("title"), default=default_title),
            description=self._safe_text(item.get("simpleExplain"), item.get("description"), item.get("eventDescription")),
            region=self._safe_text(item.get("regionName"), item.get("region")),
            startDate=self._safe_text(item.get("startDate"), item.get("eventStartDate")),
            endDate=self._safe_text(item.get("endDate"), item.get("eventEndDate")),
            thumbnail=self._safe_text(item.get("thumbnail"), item.get("thumbUrl"), item.get("imageUrl"), item.get("eventThumbnail")),
            eventStatus=self._safe_text(item.get("eventStatus"), item.get("pctStatus"), item.get("status"), item.get("paymentStatus"), item.get("refundStatus")),
            detailUrl=f"/events/{event_id}" if event_id else "",
            applyUrl=f"/events/{event_id}/apply" if event_id else "",
            scoreReason=self._safe_text(item.get("scoreReason")),
        )

    def _extract_search_keyword(self, raw_message: str) -> str | None:
        text = (raw_message or "").strip()
        cleanup_words = [
            "행사", "축제", "공연", "전시", "추천", "찾아줘", "찾아", "검색", "보여줘", "알려줘", "좀", "이번", "주말", "무료", "서울", "강남", "근처",
        ]
        for word in cleanup_words:
            text = text.replace(word, " ")
        text = " ".join(token for token in text.split() if len(token) >= 2)
        return text or None

    async def search_events(self, *, raw_message: str) -> ActionExecutionResult:
        keyword = self._extract_search_keyword(raw_message)
        items = await self.spring.search_events(keyword=keyword, page=0, size=3)
        if not items:
            return ActionExecutionResult(
                answer="조건에 맞는 행사를 찾지 못했어요. 지역이나 키워드를 조금 바꿔서 다시 말씀해 주세요.",
                action_name="search_events",
                metadata={"keyword": keyword or ""},
                next_actions=self._default_next_actions(),
            )
        cards = [self._build_event_card(item, default_title="행사") for item in items[:4]]
        reasons = []
        if keyword:
            reasons.append(f"'{keyword}' 키워드와 제목/설명이 맞는 행사")
        reasons.append("현재 공개된 행사 목록에서 검색")
        answer = "관련 행사 후보를 찾았어요. 카드에서 상세 페이지로 바로 이동할 수 있어요."
        if keyword:
            answer = f"'{keyword}'와 관련된 행사 후보를 찾았어요. 카드에서 상세 페이지로 바로 이동할 수 있어요."
        return ActionExecutionResult(
            answer=answer,
            cards=cards,
            action_name="search_events",
            metadata={"keyword": keyword or "", "itemCount": len(items)},
            recommendation_reasons=reasons,
            next_actions=[
                ChatNextAction(label="이번 주말 행사", actionType="prompt", value="이번 주말 행사 추천해줘", variant="secondary"),
                ChatNextAction(label="무료 행사만 보기", actionType="prompt", value="무료 행사만 추천해줘", variant="secondary"),
            ],
        )

    async def get_my_inquiries(self, *, authorization: str | None) -> ActionExecutionResult:
        if not authorization:
            return self._require_login_message("문의 내역을")
        data = await self.spring.get_my_inquiries(authorization)
        items = data.get("items") or data.get("content") or data.get("list") or []
        if not items:
            return ActionExecutionResult(
                answer="현재 문의 내역이 없어요.",
                action_name="get_my_inquiries",
                metadata={"itemCount": 0},
                next_actions=[ChatNextAction(label="관리자 문의 남기기", actionType="prompt", value="관리자 문의: 문의할 내용을 적어주세요", variant="primary")],
            )
        lines = ["최근 문의 내역이에요."]
        for item in items[:3]:
            title = self._safe_text(item.get("eventTitle"), item.get("title"), default="행사")
            content = self._safe_text(item.get("content"), item.get("inquiryContent"), default="문의 내용")
            status = self._safe_text(item.get("status"), item.get("answerStatus"), default="상태 확인 필요")
            lines.append(f"- {title}: {content} ({status})")
        return ActionExecutionResult(
            answer="\n".join(lines),
            action_name="get_my_inquiries",
            metadata={"itemCount": len(items)},
            next_actions=[
                ChatNextAction(label="AI 문의 확인", actionType="navigate", value="/mypage/inquiries", variant="secondary"),
                ChatNextAction(label="관리자 문의 남기기", actionType="prompt", value="관리자 문의: ", variant="primary"),
            ],
        )

    async def get_my_participations(self, *, authorization: str | None) -> ActionExecutionResult:
        if not authorization:
            return self._require_login_message("참여 행사 상태를")
        items = await self.spring.get_my_participations(authorization)
        if not items:
            return ActionExecutionResult(answer="현재 참여 행사 내역이 없어요.", action_name="get_my_participations", metadata={"itemCount": 0}, next_actions=self._default_next_actions())
        cards = [self._build_event_card(item, default_title="참여 행사") for item in items[:3]]
        lines = ["최근 참여 행사 상태예요."]
        for item in items[:3]:
            title = self._safe_text(item.get("eventTitle"), item.get("title"), default="행사")
            status = self._safe_text(item.get("pctStatus"), item.get("status"), default="상태 확인 필요")
            start = self._safe_text(item.get("eventStartDate"), item.get("startDate"))
            end = self._safe_text(item.get("eventEndDate"), item.get("endDate"))
            period = " ~ ".join([value for value in [start, end] if value])
            lines.append(f"- {title}: {status}" + (f" ({period})" if period else ""))
        return ActionExecutionResult(answer="\n".join(lines), cards=cards, action_name="get_my_participations", metadata={"itemCount": len(items)}, next_actions=[ChatNextAction(label="결제 상태 보기", actionType="prompt", value="내 결제 상태 보여줘", variant="secondary"), ChatNextAction(label="환불 상태 보기", actionType="prompt", value="내 환불 상태 알려줘", variant="secondary")])

    async def get_my_wishlist(self, *, authorization: str | None) -> ActionExecutionResult:
        if not authorization:
            return self._require_login_message("관심 행사 목록을")
        items = await self.spring.get_my_wishlist(authorization)
        if not items:
            return ActionExecutionResult(answer="현재 관심 행사 목록이 비어 있어요.", action_name="get_my_wishlist", metadata={"itemCount": 0}, next_actions=self._default_next_actions())
        cards = [self._build_event_card(item, default_title="관심 행사") for item in items[:3]]
        return ActionExecutionResult(answer="최근 관심 행사 목록이에요. 카드에서 바로 다시 확인할 수 있어요.", cards=cards, action_name="get_my_wishlist", metadata={"itemCount": len(items)}, next_actions=[ChatNextAction(label="관심 기반 추천", actionType="prompt", value="내 관심 행사 기준으로 추천해줘", variant="primary")])

    async def get_my_payment_statuses(self, *, authorization: str | None) -> ActionExecutionResult:
        if not authorization:
            return self._require_login_message("결제 상태를")
        items = await self.spring.get_my_payment_statuses(authorization)
        if not items:
            return ActionExecutionResult(answer="현재 조회되는 결제 내역이 없어요.", action_name="get_my_payment_statuses", metadata={"itemCount": 0}, next_actions=[ChatNextAction(label="참여 내역 보기", actionType="prompt", value="내 참여 행사 보여줘", variant="secondary")])
        lines = ["최근 결제 상태예요."]
        cards: list[ChatCard] = []
        for item in items[:3]:
            title = self._safe_text(item.get("eventTitle"), default="행사")
            pay_type = self._safe_text(item.get("payType"), default="결제")
            pay_status = self._safe_text(item.get("paymentStatus"), default="상태 확인 필요")
            amount = self._safe_text(item.get("amountTotal"), default="0")
            lines.append(f"- {title}: {pay_status} / {pay_type} / {amount}원")
            cards.append(self._build_event_card(item, default_title=title))
        return ActionExecutionResult(answer="\n".join(lines), cards=cards, action_name="get_my_payment_statuses", metadata={"itemCount": len(items)}, next_actions=[ChatNextAction(label="환불 상태 보기", actionType="prompt", value="내 환불 상태 알려줘", variant="secondary"), ChatNextAction(label="문의 남기기", actionType="prompt", value="관리자 문의: 결제 관련 문의가 있어요", variant="primary")])

    async def get_my_refund_statuses(self, *, authorization: str | None) -> ActionExecutionResult:
        if not authorization:
            return self._require_login_message("환불 상태를")
        items = await self.spring.get_my_refund_statuses(authorization)
        if not items:
            return ActionExecutionResult(answer="현재 조회되는 환불 내역이 없어요.", action_name="get_my_refund_statuses", metadata={"itemCount": 0}, next_actions=[ChatNextAction(label="환불 규정 보기", actionType="prompt", value="환불 규정 알려줘", variant="secondary")])
        lines = ["최근 환불 처리 상태예요."]
        cards: list[ChatCard] = []
        for item in items[:3]:
            title = self._safe_text(item.get("eventTitle"), default="행사")
            refund_status = self._safe_text(item.get("refundStatus"), item.get("paymentStatus"), default="상태 확인 필요")
            canceled_amount = self._safe_text(item.get("canceledAmount"), default="0")
            lines.append(f"- {title}: {refund_status} / 환불 금액 {canceled_amount}원")
            cards.append(self._build_event_card(item, default_title=title))
        return ActionExecutionResult(answer="\n".join(lines), cards=cards, action_name="get_my_refund_statuses", metadata={"itemCount": len(items)}, next_actions=[ChatNextAction(label="환불 규정 보기", actionType="prompt", value="환불 규정 알려줘", variant="secondary"), ChatNextAction(label="관리자 문의", actionType="prompt", value="관리자 문의: 환불 상태 확인 부탁드려요", variant="primary")])

    async def get_my_booth_statuses(self, *, authorization: str | None) -> ActionExecutionResult:
        if not authorization:
            return self._require_login_message("부스 신청 상태를")
        items = await self.spring.get_my_booth_statuses(authorization)
        if not items:
            return ActionExecutionResult(answer="현재 조회되는 부스 신청 내역이 없어요.", action_name="get_my_booth_statuses", metadata={"itemCount": 0}, next_actions=[ChatNextAction(label="부스 안내 보기", actionType="prompt", value="부스 신청 방법 알려줘", variant="secondary")])
        lines = ["최근 부스 신청 상태예요."]
        cards: list[ChatCard] = []
        for item in items[:3]:
            title = self._safe_text(item.get("eventTitle"), item.get("boothTitle"), default="부스")
            status = self._safe_text(item.get("status"), default="상태 확인 필요")
            total_price = self._safe_text(item.get("totalPrice"), default="0")
            lines.append(f"- {title}: {status} / 총 {total_price}원")
            cards.append(self._build_event_card(item, default_title=title))
        return ActionExecutionResult(answer="\n".join(lines), cards=cards, action_name="get_my_booth_statuses", metadata={"itemCount": len(items)}, next_actions=[ChatNextAction(label="부스 신청서 보기", actionType="navigate", value="/mypage/booths", variant="secondary"), ChatNextAction(label="부스 규정 보기", actionType="prompt", value="부스 신청 규정 알려줘", variant="secondary")])

    async def get_my_status_summary(self, *, authorization: str | None) -> ActionExecutionResult:
        if not authorization:
            return self._require_login_message("내 상태를")
        try:
            participations = await self.spring.get_my_participations(authorization)
        except Exception:
            participations = []
        try:
            wishlist = await self.spring.get_my_wishlist(authorization)
        except Exception:
            wishlist = []
        try:
            inquiries_data = await self.spring.get_my_inquiries(authorization)
            inquiries = inquiries_data.get("items") or inquiries_data.get("content") or inquiries_data.get("list") or []
        except Exception:
            inquiries = []
        try:
            payments = await self.spring.get_my_payment_statuses(authorization)
        except Exception:
            payments = []
        try:
            refunds = await self.spring.get_my_refund_statuses(authorization)
        except Exception:
            refunds = []
        try:
            booths = await self.spring.get_my_booth_statuses(authorization)
        except Exception:
            booths = []

        waiting_inquiries = 0
        for item in inquiries:
            status = self._safe_text(item.get("status"), item.get("answerStatus")).lower()
            if any(token in status for token in ["대기", "pending", "미답변"]):
                waiting_inquiries += 1

        answer = (
            "현재 내 상태를 요약해 드릴게요.\n"
            f"- 참여 행사: {len(participations)}건\n"
            f"- 관심 행사: {len(wishlist)}건\n"
            f"- 문의 내역: {len(inquiries)}건\n"
            f"- 결제 내역: {len(payments)}건\n"
            f"- 환불 내역: {len(refunds)}건\n"
            f"- 부스 신청: {len(booths)}건"
        )
        if waiting_inquiries:
            answer += f"\n- 아직 답변 대기 중인 문의: {waiting_inquiries}건"
        cards = [self._build_event_card(item, default_title="참여 행사") for item in participations[:2]]
        return ActionExecutionResult(
            answer=answer,
            cards=cards,
            action_name="get_my_status_summary",
            metadata={"participationCount": len(participations), "wishlistCount": len(wishlist), "inquiryCount": len(inquiries), "paymentCount": len(payments), "refundCount": len(refunds), "boothCount": len(booths)},
            next_actions=[
                ChatNextAction(label="결제 상태", actionType="prompt", value="내 결제 상태 보여줘", variant="secondary"),
                ChatNextAction(label="환불 상태", actionType="prompt", value="내 환불 상태 알려줘", variant="secondary"),
                ChatNextAction(label="부스 상태", actionType="prompt", value="내 부스 신청 상태 보여줘", variant="secondary"),
            ],
        )

    def get_admin_contact_help(self, *, raw_message: str, authorization: str | None) -> ActionExecutionResult:
        if not authorization:
            if any(keyword in raw_message for keyword in ["로그인", "비밀번호", "비번"]):
                answer = self._login_issue_email_guide()
            else:
                answer = "관리자 문의는 로그인한 상태에서만 접수할 수 있어요. 로그인 후 다시 이용해주세요."
        else:
            answer = self._admin_contact_prompt()
        return ActionExecutionResult(answer=answer, action_name="get_admin_contact_help", next_actions=[ChatNextAction(label="문의 형식 복사", actionType="prompt", value="관리자 문의: ", variant="primary")])

    async def submit_admin_contact(self, *, raw_message: str, authorization: str | None, session_id: str | None) -> ActionExecutionResult:
        if not authorization:
            if any(keyword in raw_message for keyword in ["로그인", "비밀번호", "비번"]):
                return ActionExecutionResult(answer=self._login_issue_email_guide(), status_code=401, action_name="submit_admin_contact")
            return ActionExecutionResult(answer="관리자 문의는 로그인한 상태에서만 접수할 수 있어요. 로그인 후 다시 보내주세요.", status_code=401, action_name="submit_admin_contact")

        content = raw_message.split(":", 1)[1].strip() if ":" in raw_message else ""
        if not content:
            return ActionExecutionResult(answer=self._admin_contact_prompt(), status_code=400, action_name="submit_admin_contact")

        submitted = await self.spring.submit_admin_contact(session_id=session_id, content=content, authorization=authorization)
        if not submitted:
            self.admin_support.save_contact(content=content, session_id=session_id, authorization=authorization)
        return ActionExecutionResult(
            answer="관리자 문의가 접수되었어요. 답변은 마이페이지 > 문의 내역 > AI 문의에서 확인할 수 있어요.",
            action_name="submit_admin_contact",
            metadata={"submittedToSpring": bool(submitted)},
            next_actions=[ChatNextAction(label="내 문의 내역 보기", actionType="prompt", value="내 문의 내역 보여줘", variant="secondary")],
        )

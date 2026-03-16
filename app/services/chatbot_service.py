from __future__ import annotations

from app.schemas.chat_schema import ChatResponse, ChatCard
from app.services.admin_support_service import AdminSupportService
from app.services.gemini_service import GeminiService
from app.services.intent_service import IntentService
from app.services.rag_service import RagService
from app.services.recommendation_service import RecommendationService
from app.services.spring_api_service import SpringApiService


class ChatbotService:
    def __init__(self):
        self.gemini = GeminiService()
        self.intent = IntentService()
        self.rag = RagService()
        self.recommender = RecommendationService()
        self.spring = SpringApiService()
        self.admin_support = AdminSupportService()

    def _admin_contact_prompt(self) -> str:
        return (
            '관리자에게 전달할 내용을 아래 형식으로 보내주세요.\n\n'
            '관리자 문의: 문의 내용\n\n'
            '예) 관리자 문의: 결제가 됐는데 신청 내역이 안 보여요'
        )

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
        try:
            raw_message = (message or '').strip()
            lowered = raw_message.lower()

            if lowered.startswith('관리자 문의:') or lowered.startswith('관리자문의:'):
                if not authorization:
                    reply = '관리자 문의는 로그인한 상태에서만 접수할 수 있어요. 로그인 후 다시 보내주세요.'
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=reply,
                        intent='admin_contact',
                        session_id=session_id,
                    )
                    return ChatResponse(answer=reply, cards=[], intent='admin_contact')

                content = raw_message.split(':', 1)[1].strip() if ':' in raw_message else ''
                if not content:
                    reply = self._admin_contact_prompt()
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=reply,
                        intent='admin_contact',
                        session_id=session_id,
                    )
                    return ChatResponse(answer=reply, cards=[], intent='admin_contact')

                self.admin_support.save_contact(
                    content=content,
                    session_id=session_id,
                    authorization=authorization,
                )
                reply = '관리자 문의가 접수되었어요. 확인 후 답변드릴게요.'
                self.admin_support.save_log(
                    question=raw_message,
                    answer=reply,
                    intent='admin_contact',
                    session_id=session_id,
                )
                return ChatResponse(answer=reply, cards=[], intent='admin_contact')

            if '관리자' in raw_message and '문의' in raw_message:
                if not authorization:
                    reply = '관리자 문의는 로그인한 상태에서만 접수할 수 있어요. 로그인 후 다시 이용해주세요.'
                else:
                    reply = self._admin_contact_prompt()
                self.admin_support.save_log(
                    question=raw_message,
                    answer=reply,
                    intent='admin_contact_help',
                    session_id=session_id,
                )
                return ChatResponse(answer=reply, cards=[], intent='admin_contact_help')

            intent = self.intent.detect(raw_message, page_type=page_type, history=history)

            if intent in {
                'refund_policy',
                'refund_method',
                'system_login',
                'system_signup',
                'system_payment',
                'system_inquiry',
                'system_mypage',
                'system_booth',
                'system_report',
                'host_help',
                'admin_contact_prompt',
            }:
                answer = await self.rag.answer(raw_message, intent=intent)
                answer = answer or '관련 안내를 찾지 못했어요.'
                self.admin_support.save_log(
                    question=raw_message,
                    answer=answer,
                    intent=intent,
                    session_id=session_id,
                )
                return ChatResponse(answer=answer, cards=[], intent=intent)

            if intent == 'my_inquiry':
                if not authorization:
                    answer = '문의 내역을 보려면 로그인이 필요해요. 로그인한 상태에서 다시 말씀해 주세요.'
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=answer,
                        intent=intent,
                        session_id=session_id,
                    )
                    return ChatResponse(answer=answer, cards=[], intent=intent)

                try:
                    data = await self.spring.get_my_inquiries(authorization)
                    items = data.get('items') or data.get('content') or data.get('list') or []
                    if not items:
                        answer = '현재 문의 내역이 없어요.'
                        self.admin_support.save_log(
                            question=raw_message,
                            answer=answer,
                            intent=intent,
                            session_id=session_id,
                        )
                        return ChatResponse(answer=answer, cards=[], intent=intent)

                    lines = ['최근 문의 내역이에요.']
                    for item in items[:3]:
                        title = item.get('eventTitle') or item.get('title') or '행사'
                        content = item.get('content') or item.get('inquiryContent') or '문의 내용'
                        status = item.get('status') or item.get('answerStatus') or '상태 확인 필요'
                        lines.append(f'- {title}: {content} ({status})')
                    answer = '\n'.join(lines)
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=answer,
                        intent=intent,
                        session_id=session_id,
                    )
                    return ChatResponse(answer=answer, cards=[], intent=intent)
                except Exception as e:
                    print('[MY_INQUIRY ERROR]', repr(e))
                    answer = '문의 내역을 불러오는 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.'
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=answer,
                        intent=intent,
                        session_id=session_id,
                        is_error=True,
                    )
                    return ChatResponse(answer=answer, cards=[], intent=intent)

            if intent == 'my_participation':
                if not authorization:
                    answer = '참여 내역을 보려면 로그인이 필요해요. 로그인한 상태에서 다시 말씀해 주세요.'
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=answer,
                        intent=intent,
                        session_id=session_id,
                    )
                    return ChatResponse(answer=answer, cards=[], intent=intent)

                try:
                    items = await self.spring.get_my_participations(authorization)
                    if not items:
                        answer = '현재 참여 행사 내역이 없어요.'
                        self.admin_support.save_log(
                            question=raw_message,
                            answer=answer,
                            intent=intent,
                            session_id=session_id,
                        )
                        return ChatResponse(answer=answer, cards=[], intent=intent)

                    lines = ['최근 참여 행사 내역이에요.']
                    for item in items[:3]:
                        title = item.get('eventTitle') or item.get('title') or '행사'
                        status = item.get('pctStatus') or item.get('status') or '상태 확인 필요'
                        period = ' ~ '.join(
                            [value for value in [item.get('eventStartDate'), item.get('eventEndDate')] if value]
                        )
                        lines.append(f"- {title}: {status}" + (f" ({period})" if period else ''))
                    answer = '\n'.join(lines)
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=answer,
                        intent=intent,
                        session_id=session_id,
                    )
                    return ChatResponse(answer=answer, cards=[], intent=intent)
                except Exception as e:
                    print('[MY_PARTICIPATION ERROR]', repr(e))
                    answer = '참여 내역을 불러오는 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.'
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=answer,
                        intent=intent,
                        session_id=session_id,
                        is_error=True,
                    )
                    return ChatResponse(answer=answer, cards=[], intent=intent)

            if intent == 'my_wishlist':
                if not authorization:
                    answer = '관심 행사 목록을 보려면 로그인이 필요해요. 로그인한 상태에서 다시 말씀해 주세요.'
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=answer,
                        intent=intent,
                        session_id=session_id,
                    )
                    return ChatResponse(answer=answer, cards=[], intent=intent)

                try:
                    items = await self.spring.get_my_wishlist(authorization)
                    if not items:
                        answer = '현재 관심 행사로 저장된 항목이 없어요.'
                        self.admin_support.save_log(
                            question=raw_message,
                            answer=answer,
                            intent=intent,
                            session_id=session_id,
                        )
                        return ChatResponse(answer=answer, cards=[], intent=intent)

                    lines = ['최근 관심 행사 목록이에요.']
                    for item in items[:3]:
                        title = item.get('eventTitle') or item.get('title') or '행사'
                        period = ' ~ '.join(
                            [
                                value
                                for value in [
                                    item.get('startDate'),
                                    item.get('endDate'),
                                ]
                                if value
                            ]
                        )
                        lines.append(f"- {title}" + (f" ({period})" if period else ''))
                    answer = '\n'.join(lines)
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=answer,
                        intent=intent,
                        session_id=session_id,
                    )
                    return ChatResponse(answer=answer, cards=[], intent=intent)
                except Exception as e:
                    print('[MY_WISHLIST ERROR]', repr(e))
                    answer = '관심 행사 목록을 불러오는 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.'
                    self.admin_support.save_log(
                        question=raw_message,
                        answer=answer,
                        intent=intent,
                        session_id=session_id,
                        is_error=True,
                    )
                    return ChatResponse(answer=answer, cards=[], intent=intent)

            if intent == 'recommend':
                answer, cards = await self.recommender.recommend(
                    message=raw_message,
                    authorization=authorization,
                    page_type=page_type,
                    region_hint=region_hint,
                    location_keywords=location_keywords,
                    filters=filters,
                )
                self.admin_support.save_log(
                    question=raw_message,
                    answer=answer,
                    intent=intent,
                    session_id=session_id,
                )
                return ChatResponse(answer=answer, cards=[ChatCard(**c) for c in cards], intent=intent)

            faq = await self.rag.answer(raw_message)
            context = faq or 'MOHAENG는 행사 추천, 검색, 문의, 환불 안내를 지원하는 플랫폼입니다.'
            reply = await self.gemini.generate(history or [], raw_message, context=context)
            self.admin_support.save_log(
                question=raw_message,
                answer=reply,
                intent='chat',
                session_id=session_id,
            )
            return ChatResponse(answer=reply, cards=[], intent='chat')

        except Exception as e:
            print('[CHATBOT ERROR]', repr(e))
            answer = '지금은 챗봇 응답을 준비하는 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.'
            self.admin_support.save_log(
                question=message,
                answer=answer,
                intent='fallback',
                session_id=session_id,
                is_error=True,
            )
            return ChatResponse(answer=answer, cards=[], intent='fallback')

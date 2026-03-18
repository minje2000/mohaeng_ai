# chatbot_service 실연결 패치

이번 패치는 `chatbot_service.py`를 아래 구조로 실제 연결한 버전이다.

- `ActionService`: 로그인 필요한 조회/등록 액션 처리
- `AnswerComposerService`: retrieval 결과를 기반으로 최종 답변/출처 조립
- `ChatbotService`: intent 분기, 서비스 조합, 로그 적재만 담당

## 현재 흐름

1. `IntentService`로 질문 성격 분류
2. 추천형이면 `RecommendationService`
3. 액션형이면 `ActionService.dispatch()`
4. 설명형이면 `RetrievalService.retrieve()` + `AnswerComposerService.compose_explanation()`
5. 일반 대화는 retrieval을 한 번 거친 뒤 `compose_general_chat()`으로 처리

## 다음 단계

- `IntentService`에서 설명형 intent 축소
- `ActionService`에 결제 상태 / 환불 진행 / 부스 신청 상태 확장
- `AnswerComposerService`에서 프롬프트 세분화
- 관리자 화면에서 `routeType`, `usedGemini`, `sourceCount` 노출 강화

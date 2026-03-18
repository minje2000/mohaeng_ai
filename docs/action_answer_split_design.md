# Action / Answer Composer 분리 설계

## 1. 목적
기존 `chatbot_service.py`에 몰린 책임을 분리해서 유지보수를 쉽게 만든다.

- `ActionService`: Spring API 호출과 관리자 문의 접수 담당
- `AnswerComposerService`: Retrieval 결과를 최종 답변으로 조립

## 2. 권장 호출 흐름

### 액션형
1. `intent_service.detect()`
2. `action_service.dispatch()`
3. `chatbot_service`는 로그 적재와 `ChatResponse` 반환만 수행

### 설명형
1. `intent_service.detect()`
2. `retrieval_service.retrieve()`
3. `answer_composer_service.compose_explanation()`
4. `chatbot_service`는 로그 적재와 `ChatResponse` 반환만 수행

## 3. 다음 단계 리팩토링 포인트
- `chatbot_service.py`의 관리자 문의, 내 문의, 내 참여, 내 관심행사 분기 제거
- `_compose_explanation()` 제거 후 `AnswerComposerService` 사용
- 로그 metadata에 `action_name`, `usedGemini`, `sourceCount` 적재
- 추후 결제 상태 / 환불 상태 API 추가 시 `ActionService`에만 메서드 추가

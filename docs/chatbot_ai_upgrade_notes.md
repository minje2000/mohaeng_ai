# 챗봇 AI 구조 개선 메모

이번 개편의 핵심은 챗봇 진입점을 규칙 intent 분기 중심에서 `행동형 액션 + 검색형 설명` 구조로 바꾸는 것이다.

## 바뀐 점
- `chatbot_service.py`에서 먼저 액션/추천/검색형을 고른다.
- 설명형 질문은 기본적으로 `retrieval_service.py`로 보낸다.
- `action_service.py`가 행사 찾기, 내 상태 확인, 문의 내역, 참여 상태, 관심 행사, 관리자 문의를 담당한다.
- `answer_composer_service.py`가 검색 결과를 기반으로 Gemini 답변을 조립한다.
- `data/rag/*.md` 문서를 세분화해서 ChromaDB 검색 정확도를 높인다.

## 기대 효과
- 챗봇이 먼저 문서를 이해하고 답하는 느낌이 강해진다.
- 규칙 분기가 줄어들고, 질문 표현이 달라도 의미 검색으로 대응할 수 있다.
- 행사 찾기 / 정책 이해 / 내 상태 확인 / 추천 받기 / 문의 남기기를 한 채널 안에서 처리하기 쉬워진다.

## 운영 체크
- 문서를 수정했으면 `python -m app.scripts.rebuild_chroma` 실행
- `GET /ai/admin/retrieval/status` 로 인덱스 상태 확인

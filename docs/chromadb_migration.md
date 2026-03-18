# ChromaDB 적용 메모

## 현재 구조
- 문서 원본: `data/rag/*.md`
- 벡터 저장소: `data/chroma/`
- 컬렉션 이름: `mohaeng_rag`
- 임베딩 모델: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

## 인덱스 재생성
```bash
python -m app.scripts.rebuild_chroma
```

## 확인 API
- `GET /ai/admin/retrieval/status`
- `POST /ai/admin/retrieval/rebuild`

## 운영 원칙
1. 설명형 질문은 Chroma 검색 우선
2. 액션형 질문은 Spring API 우선
3. 추천형 질문은 RecommendationService 우선
4. Gemini는 검색 결과를 정리하는 역할로 사용

## 문서 추가 규칙
- 1개 정책 = 1개 markdown 파일 권장
- 큰 문서는 섹션별 `##` 제목 필수
- 환불/문의/마이페이지/부스/신고는 분리 문서 권장

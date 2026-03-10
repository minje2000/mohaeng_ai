import json
from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from typing import Optional

from app.core.security import require_internal_api_key
from app.schemas.reco_schema import RecommendRequest, EmbeddingRequest, EmbeddingResponse
from app.services import reco_service

router = APIRouter(prefix="/ai", tags=["AI 추천"])


@router.post("/recommend", dependencies=[Depends(require_internal_api_key)])
def recommend(req: RecommendRequest):
    """행사 AI 추천 - 유사도 계산 후 상위 6개 event_id 반환"""
    try:
        events = [{"event_id": e.event_id, "embedding": e.embedding} for e in req.events]
        result = reco_service.recommend_events(req.user_text, events)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/embedding", dependencies=[Depends(require_internal_api_key)])
def create_embedding(req: EmbeddingRequest):
    """단일 텍스트 임베딩 생성 (행사 등록 시 Spring Boot에서 호출)"""
    try:
        vector = reco_service.get_embedding(req.text)
        return EmbeddingResponse(embedding=json.dumps(vector))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/suggest-tags", dependencies=[Depends(require_internal_api_key)])
async def suggest_tags(
    title: str = Form(...),
    simple_explain: str = Form(...),
    thumbnail: Optional[UploadFile] = File(None)
):
    """행사 제목 + 한줄설명 + 썸네일 → 카테고리/주제/해시태그 추천"""
    image_bytes = None
    if thumbnail:
        image_bytes = await thumbnail.read()

    try:
        result = reco_service.suggest_tags(title, simple_explain, image_bytes)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

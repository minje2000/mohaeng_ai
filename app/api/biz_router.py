from fastapi import APIRouter
from app.schemas.biz_schema import BizOcrRequest, BizOcrResponse
from app.services.biz_service import extract_and_verify_biz

router = APIRouter(prefix="/biz", tags=["biz"])

@router.post("/signup/ocr", response_model=BizOcrResponse)
async def biz_ocr(req: BizOcrRequest):
    return await extract_and_verify_biz(req.imageBase64)

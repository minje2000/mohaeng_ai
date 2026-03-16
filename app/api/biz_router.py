from fastapi import APIRouter, Depends
from app.schemas.biz_schema import BizOcrRequest, BizOcrResponse
from app.services.biz_service import extract_and_verify_biz
from app.core.security import verify_api_key

router = APIRouter(prefix="/ai", tags=["Biz Signup OCR"], dependencies=[Depends(verify_api_key)])

@router.post("/bizOcr", response_model=BizOcrResponse)
async def biz_ocr(req: BizOcrRequest):
    return await extract_and_verify_biz(req.imageBase64)

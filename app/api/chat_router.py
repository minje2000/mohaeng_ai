
from fastapi import APIRouter, Depends, Header
from app.core.security import verify_api_key
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chatbot_service import ChatbotService

router = APIRouter(prefix='/ai', tags=['AI Chat'])
service = ChatbotService()


@router.post('/chat', response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(req: ChatRequest, authorization: str | None = Header(default=None)):
    auth = req.authorization or authorization
    history = [item.model_dump() for item in req.history] if req.history else []
    return await service.chat(
        message=req.message,
        authorization=auth,
        history=history,
        session_id=req.sessionId,
        page_type=req.pageType,
        region_hint=req.region,
        location_keywords=req.locationKeywords,
        filters=req.filters,
    )

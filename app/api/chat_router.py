from fastapi import APIRouter, Depends, Header, Query
from app.core.security import verify_api_key
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.admin_support_service import AdminSupportService
from app.services.chatbot_service import ChatbotService

router = APIRouter(prefix='/ai', tags=['AI Chat'])
service = ChatbotService()
admin_support = AdminSupportService()


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


@router.get('/admin/contacts', dependencies=[Depends(verify_api_key)])
async def list_contacts(limit: int = Query(default=100, ge=1, le=500)):
    return {'items': admin_support.list_contacts(limit=limit)}


@router.get('/admin/logs', dependencies=[Depends(verify_api_key)])
async def list_logs(limit: int = Query(default=150, ge=1, le=1000)):
    return {'items': admin_support.list_logs(limit=limit)}

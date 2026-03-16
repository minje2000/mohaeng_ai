from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import verify_api_key
from app.services.admin_support_service import AdminSupportService

router = APIRouter(prefix='/ai/admin', tags=['AI Admin'], dependencies=[Depends(verify_api_key)])
admin_support = AdminSupportService()


class ContactAnswerRequest(BaseModel):
    answer: str
    status: str = '답변완료'


@router.get('/contacts')
async def list_contacts(limit: int = 100):
    return {
        'items': admin_support.list_contacts(limit=limit),
    }


@router.put('/contacts/{item_id}')
async def answer_contact(item_id: str, req: ContactAnswerRequest):
    updated = admin_support.answer_contact(item_id=item_id, answer=req.answer, status=req.status)
    return updated or {'message': 'not_found'}


@router.get('/logs')
async def list_logs(limit: int = 200):
    return {
        'summary': admin_support.summarize_logs(),
        'items': admin_support.list_logs(limit=limit),
    }

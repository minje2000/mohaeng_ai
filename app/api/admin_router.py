from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import verify_api_key
from app.services.admin_support_service import AdminSupportService
from app.services.chat_log_service import ChatLogService
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix='/ai/admin', tags=['AI Admin'], dependencies=[Depends(verify_api_key)])
admin_support = AdminSupportService()
chat_logs = ChatLogService()
retrieval = RetrievalService()


class ContactUpdateRequest(BaseModel):
    answer: str | None = None
    status: str | None = None
    assignee: str | None = None
    category: str | None = None
    priority: str | None = None
    memo: str | None = None


@router.get('/contacts')
async def list_contacts(limit: int = 100):
    return {'items': admin_support.list_contacts(limit=limit)}


@router.put('/contacts/{item_id}')
async def update_contact(item_id: str, req: ContactUpdateRequest):
    updated = admin_support.update_contact(
        item_id=item_id,
        answer=req.answer,
        status=req.status,
        assignee=req.assignee,
        category=req.category,
        priority=req.priority,
        memo=req.memo,
        actor=req.assignee or '관리자',
    )
    if not updated:
        raise HTTPException(status_code=404, detail='contact_not_found')
    return updated


@router.delete('/contacts/{item_id}')
async def delete_contact(item_id: str):
    deleted = admin_support.delete_contact(item_id=item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='contact_not_found')
    return {'ok': True, 'itemId': item_id}


@router.post('/contacts/{item_id}/delete')
async def delete_contact_post(item_id: str):
    deleted = admin_support.delete_contact(item_id=item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='contact_not_found')
    return {'ok': True, 'itemId': item_id}


@router.get('/logs')
async def list_logs(limit: int = 200):
    return {'summary': chat_logs.summarize(), 'items': chat_logs.list_recent(limit=limit)}


@router.get('/retrieval/status')
async def retrieval_status():
    return retrieval.get_status()


@router.post('/retrieval/rebuild')
async def retrieval_rebuild():
    return retrieval.rebuild_index(force=True)

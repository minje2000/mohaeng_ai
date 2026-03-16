from fastapi import APIRouter, Depends, Header, HTTPException

from app.core.config import settings
from app.schemas.moderation_schema import (
    EventModerationRequest,
    EventModerationResponse,
)
from app.services.watsonx_moderation_service import WatsonxModerationService

router = APIRouter(prefix="/ai/moderation", tags=["moderation"])


def verify_internal_api_key(x_api_key: str = Header(default="")):
    if x_api_key != settings.APP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post(
    "/event",
    response_model=EventModerationResponse,
    dependencies=[Depends(verify_internal_api_key)],
)
def moderate_event(req: EventModerationRequest):
    service = WatsonxModerationService()
    return service.evaluate_event(req)
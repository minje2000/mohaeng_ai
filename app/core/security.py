# app/core/security.py
# STS 에서 내부 호출 보호
from fastapi import Header, HTTPException
from app.core.config import settings
def require_internal_api_key(x_api_key: str | None = Header(default=None)):
    if x_api_key != settings.APP_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized (invalid x-api-key)")

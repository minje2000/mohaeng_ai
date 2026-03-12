from pydantic import BaseModel, Field
from typing import Optional, List


class EventModerationRequest(BaseModel):
    title: str = Field(..., min_length=1)
    simple_explain: Optional[str] = None
    description: Optional[str] = None
    lot_number_adr: Optional[str] = None
    detail_adr: Optional[str] = None
    topic_ids: Optional[str] = None
    hashtag_ids: Optional[str] = None


class EventModerationResponse(BaseModel):
    risk_score: float
    reasons: List[str] = []
    summary: str = ""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class EventModerationRequest(BaseModel):
    title: str = Field(..., min_length=1)
    simple_explain: Optional[str] = None
    description: Optional[str] = None
    lot_number_adr: Optional[str] = None
    detail_adr: Optional[str] = None

    # 기존 연동 유지용
    topic_ids: Optional[str] = None
    hashtag_ids: Optional[str] = None

    # 정확도 향상용: 가능하면 앞으로는 ID 대신 "이름"도 같이 보내는 걸 추천
    topic_names: List[str] = Field(default_factory=list)
    hashtag_names: List[str] = Field(default_factory=list)


class EventModerationResponse(BaseModel):
    # 기존 필드 유지
    risk_score: float
    reasons: List[str] = Field(default_factory=list)
    summary: str = ""

    # 추가 필드
    decision: Literal["ALLOW", "REVIEW"] = "REVIEW"
    confidence: float = 0.0
    categories: List[str] = Field(default_factory=list)
    parse_ok: bool = True
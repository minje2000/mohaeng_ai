from pydantic import BaseModel, Field
from typing import Any, List, Optional


class ChatHistoryItem(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    authorization: Optional[str] = None
    history: List[ChatHistoryItem] = []
    sessionId: Optional[str] = None
    pageType: Optional[str] = None
    contextPage: Optional[str] = None
    region: Optional[str] = None
    locationKeywords: List[str] = []
    filters: Optional[dict[str, Any]] = None


class ChatCard(BaseModel):
    eventId: Optional[int] = None
    title: str
    description: Optional[str] = None
    region: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    thumbnail: Optional[str] = None
    eventStatus: Optional[str] = None
    detailUrl: Optional[str] = None
    applyUrl: Optional[str] = None
    scoreReason: Optional[str] = None


class ChatSource(BaseModel):
    type: str
    title: str
    snippet: str


class ChatNextAction(BaseModel):
    label: str
    actionType: str
    value: Optional[str] = None
    variant: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    cards: List[ChatCard] = []
    sources: List[ChatSource] = []
    recommendationReasons: List[str] = []
    nextActions: List[ChatNextAction] = []
    intent: Optional[str] = None
    routeType: Optional[str] = None

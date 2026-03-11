from pydantic import BaseModel
from typing import List, Optional

class EventEmbedding(BaseModel):
    event_id: int
    embedding: str
    region_id: Optional[int] = None

class RecommendRequest(BaseModel):
    user_text: str
    user_region_ids: Optional[List[int]] = []
    events: List[EventEmbedding]

class EmbeddingRequest(BaseModel):
    text: str

class EmbeddingResponse(BaseModel):
    embedding: str

class TagSuggestResponse(BaseModel):
    categoryId: int
    topicIds: List[int]
    hashtagNames: List[str]
    simpleExplain: str
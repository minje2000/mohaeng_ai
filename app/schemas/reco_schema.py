from pydantic import BaseModel
from typing import List, Optional

class EventEmbedding(BaseModel):
    event_id: int
    embedding: str

class RecommendRequest(BaseModel):
    user_text: str
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

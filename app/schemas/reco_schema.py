from pydantic import BaseModel


class EventEmbedding(BaseModel):
    event_id: int
    embedding: str  # JSON 문자열 "[0.1, 0.2, ...]"


class RecommendRequest(BaseModel):
    user_text: str
    events: list[EventEmbedding]


class EmbeddingRequest(BaseModel):
    text: str


class EmbeddingResponse(BaseModel):
    embedding: str  # JSON 문자열


class TagSuggestResponse(BaseModel):
    categoryId: int
    topicIds: list[int]
    hashtagNames: list[str]

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class CreateSessionRequest(BaseModel):
    user_id: uuid.UUID
    story_id: uuid.UUID

class SendMessageRequest(BaseModel):
    message: str

class CitationResponse(BaseModel):
    article_id: uuid.UUID
    publisher_name: str
    published_at: datetime
    title: str
    similarity: float
    confidence: float

    class Config:
        from_attributes = True

class ChatMessageResponse(BaseModel):
    id: int
    session_id: uuid.UUID
    sender: str
    message: str
    citations: List[CitationResponse] = []
    prompt_version: str
    chat_metadata: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    story_id: uuid.UUID
    title: Optional[str]
    message_count: int
    messages: List[ChatMessageResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatSessionSimpleResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    story_id: uuid.UUID
    title: Optional[str]
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatHealthResponse(BaseModel):
    llm_provider: str
    configured_model: str
    prompt_version: str
    conversation_engine_version: str
    streaming_enabled: bool
    api_key_configured: bool
    avg_response_latency_ms: float
    total_sessions: int
    total_messages: int
    retriever_status: str
    provider_health: str
    qdrant_status: str

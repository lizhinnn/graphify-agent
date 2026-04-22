from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class SessionInfo(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MessageInfo(BaseModel):
    id: Optional[int]
    session_id: str
    role: str
    content: str
    is_thought: bool
    created_at: datetime

    class Config:
        from_attributes = True

class SessionListResponse(BaseModel):
    sessions: List[SessionInfo]

class SessionMessagesResponse(BaseModel):
    messages: List[MessageInfo]

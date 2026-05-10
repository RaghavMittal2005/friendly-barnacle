from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class Message(BaseModel):
    """Single message in conversation"""
    role: MessageRole
    content: str

class Recommendation(BaseModel):
    """Single recommendation with reasoning"""
    id: str = Field(..., description="Product ID")
    name: str
    url: str
    duration_minutes: Optional[int] = None
    category: str
    reason: str

class ChatRequest(BaseModel):
    """POST /chat request body"""
    messages: List[Message] = Field(
        ..., 
        description="Full conversation history"
    )

class ChatResponse(BaseModel):
    """POST /chat response body"""
    reply: str = Field(..., description="Agent's text response")
    recommendations: List[Recommendation] = Field(
        default_factory=list,
        description="0-10 recommended assessments"
    )
    end_of_conversation: bool = Field(
        default=False,
        description="Whether user is satisfied"
    )

class HealthResponse(BaseModel):
    """GET /health response"""
    status: str
    catalog_loaded: bool = False
    llm_available: bool = False

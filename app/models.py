import os

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from dotenv import load_dotenv
load_dotenv()
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
import json
from uuid import uuid4
from upstash_redis import Redis

r = Redis(
    url=os.getenv("UPSTASH_REDIS_REST_URL"),   # from dashboard
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN")                   # from dashboard
)

def get_history(session_id: str) -> list:
    data = r.get(session_id)
    return json.loads(data) if data else []

def save_history(session_id: str, history: list):
    r.setex(session_id, 3600, json.dumps(history))

def delete_history(session_id: str):
    r.delete(session_id)
class ChatRequest(BaseModel):
    message: str  # just the latest user message
    session_id: Optional[str] = None  # None on first turn

class ChatResponse(BaseModel):
    reply: str
    recommendations: List[Recommendation] = Field(default_factory=list)
    end_of_conversation: bool = False
    session_id: str  # client stores this and sends it back next turn

class HealthResponse(BaseModel):
    """GET /health response"""
    status: str
    catalog_loaded: bool = False
    llm_available: bool = False

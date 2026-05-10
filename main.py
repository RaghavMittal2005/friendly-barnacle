import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from app.config import *
from app.models import ChatRequest, ChatResponse, HealthResponse, Message
from app.data.catalog_service import CatalogService
from app.ai.llm_service import LLMService
from app.logic.conversation_manager import ConversationManager

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Global services
catalog_service: CatalogService = None
llm_service: LLMService = None
conversation_manager: ConversationManager = None

@app.on_event("startup")
async def startup_event():
    """Initialize services"""
    global catalog_service, llm_service, conversation_manager
    
    try:
        print("=" * 60)
        print("Initializing SHL Assessment Recommender...")
        print("=" * 60)
        
        # Load catalog
        catalog_service = CatalogService()
        catalog_service.load_catalog(CATALOG_PATH)
        
        # Initialize LLM
        print("Initializing LLM service...")
        llm_service = LLMService()
        print("LLM service initialized ✓")
        
        # Initialize conversation manager
        conversation_manager = ConversationManager(catalog_service, llm_service)
        
        print("=" * 60)
        print("✓ All services initialized successfully!")
        print(f"✓ Catalog has {len(catalog_service.catalog)} products")
        print("=" * 60)
    
    except Exception as e:
        print(f"ERROR during startup: {e}")
        raise

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        catalog_loaded=catalog_service is not None and len(catalog_service.catalog) > 0,
        llm_available=llm_service is not None
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process user message and return agent response.
    
    Takes: Full conversation history
    Returns: Agent reply + recommendations + end_of_conversation flag
    """
    try:
        # Validation
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        if len(request.messages) > MAX_CONVERSATION_TURNS:
            raise HTTPException(status_code=400, detail=f"Max {MAX_CONVERSATION_TURNS} turns exceeded")
        
        # Get latest user message
        user_message = request.messages[-1].content
        
        # Convert to conversation history (exclude last message)
        history = [
            {"role": m.role.value, "content": m.content}
            for m in request.messages[:-1]
        ]
        
        # Process with conversation manager
        result = conversation_manager.process_message(user_message, history)
        
        # Build response
        response = ChatResponse(
            reply=result["reply"],
            recommendations=result["recommendations"],
            end_of_conversation=result["end_of_conversation"]
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /chat: {e}")
        return ChatResponse(
            reply="I encountered an error processing your request. Please try again.",
            recommendations=[],
            end_of_conversation=False
        )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SHL Assessment Recommender API",
        "docs": "/docs",
        "health": "/health",
        "chat": "/chat (POST)"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )

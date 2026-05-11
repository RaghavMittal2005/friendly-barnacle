import os
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from app.config import *
from app.models import ChatRequest, ChatResponse, HealthResponse, Message, MessageRole,r,save_history,delete_history,get_history
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
    try:
        # Load or create session
        session_id = request.session_id or str(uuid4())
        history = get_history(session_id)

        if len(history) > MAX_CONVERSATION_TURNS * 2:
            raise HTTPException(status_code=400, detail=f"Max {MAX_CONVERSATION_TURNS} turns exceeded")

        # Process message
        result = conversation_manager.process_message(request.message, history)

        # Append both turns and save
        history.append({"role": "user",      "content": request.message})
        history.append({"role": "assistant", "content": result["reply"]})
        save_history(session_id, history)

        # Clear session if conversation ended
        if result["end_of_conversation"]:
            delete_history(session_id)

        return ChatResponse(
            reply=result["reply"],
            recommendations=result["recommendations"],
            end_of_conversation=result["end_of_conversation"],
            session_id=session_id
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /chat: {e}")
        return ChatResponse(
            reply="I encountered an error. Please try again.",
            recommendations=[],
            end_of_conversation=False,
            session_id=request.session_id or str(uuid4())
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

import logging
import asyncio
import json
import threading
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from strands import Agent
from strands.session.file_session_manager import FileSessionManager
from strands.agent.conversation_manager import SummarizingConversationManager
import uvicorn
from core.config import settings

logger = logging.getLogger(__name__)

# Session Configuration
SESSION_DIR = Path(__file__).parent.parent / "sessions"
SESSION_DIR.mkdir(exist_ok=True)

class MultiSessionManager:
    """Manages multiple agent sessions, one per user or autonomous task"""
    
    def __init__(self, agent_factory):
        self.agents = {}  # session_id -> Agent
        self.session_managers = {}  # session_id -> FileSessionManager
        self._lock = threading.Lock()
        self.agent_factory = agent_factory
    
    def get_or_create_agent(self, session_id: str) -> Agent:
        """Get or create an agent for a given session ID"""
        with self._lock:
            if session_id not in self.agents:
                # Create FileSessionManager for this session (persistence)
                # Note: FileSessionManager takes storage_dir, not session_file
                session_manager = FileSessionManager(
                    session_id=session_id,
                    storage_dir=str(SESSION_DIR)
                )
                self.session_managers[session_id] = session_manager
                
                # Create SummarizingConversationManager (context window management)
                conversation_manager = SummarizingConversationManager(
                    summary_ratio=0.4,  # Summarize 40% of messages when context reduction is needed
                    preserve_recent_messages=10,  # Always keep 10 most recent messages
                )
                
                # Create agent for this session with both managers
                agent = self.agent_factory(session_manager, conversation_manager)
                self.agents[session_id] = agent
                
                logger.info(f"📁 Created new session: {session_id} in {SESSION_DIR} (Total: {len(self.agents)} sessions)")
            
            return self.agents[session_id]
    
    def get_session_count(self) -> int:
        """Get the number of active sessions"""
        with self._lock:
            return len(self.agents)
    
    def list_session_ids(self) -> list:
        """Get list of all active session IDs"""
        with self._lock:
            return list(self.agents.keys())

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str

class AgentServer:
    """FastAPI server for agent communication with session management"""
    
    def __init__(self, agent_factory):
        self.session_manager = MultiSessionManager(agent_factory)
        self.app = FastAPI(title="DevOps Agent API", version=settings.API_VERSION)
        self.server = None
        self.server_thread = None
        
        # Add CORS middleware for Streamlit UI
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify allowed origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize the default agent
        self.session_manager.get_or_create_agent("default")
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.post("/api/chat", response_model=ChatResponse)
        async def chat(request: ChatRequest):
            """Send a message to the agent and get a response (non-streaming)"""
            try:
                agent = self.session_manager.get_or_create_agent(request.session_id)
                response = agent(request.message)
                return ChatResponse(
                    response=str(response),
                    session_id=request.session_id
                )
            except Exception as e:
                logger.error(f"Error in chat endpoint: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/chat/stream")
        async def chat_stream(request: ChatRequest):
            """Send a message to the agent and stream the response"""
            async def event_stream():
                try:
                    agent = self.session_manager.get_or_create_agent(request.session_id)
                    async for chunk in agent.stream_async(request.message):
                        # Format as Server-Sent Events
                        chunk_data = {
                            "text": str(chunk),
                            "session_id": request.session_id
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                    # Send done event
                    yield f"data: {json.dumps({'done': True, 'session_id': request.session_id})}\n\n"
                except Exception as e:
                    logger.error(f"Error in stream: {e}", exc_info=True)
                    error_data = {
                        "error": str(e),
                        "session_id": request.session_id
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
            
            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable buffering for nginx
                }
            )
        
        @self.app.get("/api/health")
        async def health():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "sessions": self.session_manager.get_session_count(),
                "session_ids": self.session_manager.list_session_ids()
            }
        
        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "name": "DevOps Agent API",
                "version": settings.API_VERSION,
                "endpoints": {
                    "chat": "/api/chat",
                    "chat_stream": "/api/chat/stream",
                    "health": "/api/health"
                }
            }
    
    async def start(self):
        """Start the FastAPI server using uvicorn in a separate thread (non-blocking)"""
        config = uvicorn.Config(
            self.app,
            host=settings.API_HOST,
            port=settings.API_PORT,
            log_level="info"
        )
        self.server = uvicorn.Server(config)
        
        logger.info(f"🚀 Starting FastAPI server on http://{settings.API_HOST}:{settings.API_PORT}")
        logger.info(f"   POST /api/chat - Non-streaming chat")
        logger.info(f"   POST /api/chat/stream - Streaming chat (SSE)")
        logger.info(f"   GET  /api/health - Health check")
        
        # Run server in a separate thread (non-blocking, like the old A2AServer implementation)
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="fastapi-server"
        )
        self.server_thread.start()
        # Give the server a moment to start
        await asyncio.sleep(1)
    
    def _run_server(self):
        """Run the uvicorn server (blocking, runs in separate thread)"""
        try:
            # Run the async server in a new event loop for this thread
            asyncio.run(self.server.serve())
        except Exception as e:
            logger.error(f"FastAPI server error: {e}", exc_info=True)
    
    async def stop(self):
        """Stop the server"""
        if self.server:
            logger.info("Stopping FastAPI server...")
            self.server.should_exit = True
            self.server_thread = None

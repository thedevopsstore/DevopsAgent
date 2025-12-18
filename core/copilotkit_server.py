"""
CopilotKit server using ag-ui-strands to expose Strands agents to CopilotKit.
"""
import logging
import threading
from pathlib import Path
from typing import Callable
from contextlib import asynccontextmanager
from fastapi import FastAPI
from strands import Agent
from strands.session.file_session_manager import FileSessionManager
from strands.agent.conversation_manager import SummarizingConversationManager
from ag_ui_strands import StrandsAgent, create_strands_app
from core.config import settings

logger = logging.getLogger(__name__)

# Session Configuration
SESSION_DIR = Path(__file__).parent.parent / "sessions"
SESSION_DIR.mkdir(exist_ok=True)


class MultiSessionManager:
    """Manages multiple agent sessions, one per user or autonomous task"""
    
    def __init__(self, agent_factory: Callable):
        self.agents = {}  # session_id -> Agent
        self.session_managers = {}  # session_id -> FileSessionManager
        self._lock = threading.Lock()
        self.agent_factory = agent_factory
    
    def get_or_create_agent(self, session_id: str) -> Agent:
        """Get or create an agent for a given session ID"""
        with self._lock:
            if session_id not in self.agents:
                # Create FileSessionManager for this session (persistence)
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


def create_app(agent_factory: Callable, lifespan=None) -> FastAPI:
    """
    Create the FastAPI app with Strands agent wrapped in StrandsAgent.
    This follows the pattern from the CopilotKit AWS Strands example.
    
    Args:
        agent_factory: Function that creates an agent instance given (session_manager, conversation_manager)
        lifespan: Optional lifespan context manager for startup/shutdown events
    
    Returns:
        FastAPI app instance
    """
    # Create session manager and get default agent
    session_manager = MultiSessionManager(agent_factory)
    default_agent = session_manager.get_or_create_agent("default")
    
    # Wrap agent with StrandsAgent (matching the example pattern)
    agui_agent = StrandsAgent(
        agent=default_agent,
        name="devops_supervisor",
        description="DevOps Supervisor Agent that coordinates specialized agents for infrastructure monitoring and management.",
    )
    
    # Create the FastAPI app (matching the example pattern)
    # Note: create_strands_app might not support lifespan directly, so we'll handle it differently
    app = create_strands_app(agui_agent, "/")
    
    # Store session_manager in app state for access
    app.state.session_manager = session_manager
    
    # If lifespan is provided, we need to wrap it
    # Since create_strands_app returns a FastAPI app, we can add lifespan events
    if lifespan:
        # Store lifespan for later use
        app.state.lifespan = lifespan
    
    logger.info("✅ CopilotKit server created")
    
    return app

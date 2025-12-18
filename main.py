import asyncio
import logging
from contextlib import asynccontextmanager
from core.config import settings
from core.copilotkit_server import create_app
#from core.email_polling import start_email_polling, stop_email_polling
from agents.supervisor import create_supervisor_agent, initialize_subagents, cleanup_subagents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enable debug logging for strands to see agent thought process (optional)
# logging.getLogger("strands").setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager for FastAPI app startup/shutdown"""
    # Startup: Initialize sub-agents
    print("🚀 Starting DevOps Agent with CopilotKit...")
    await initialize_subagents()
    
    # Print startup info
    session_manager = app.state.session_manager
    print("\n" + "=" * 60)
    print("🎯 DevOps Supervisor Agent Server Running!")
    print("=" * 60)
    print(f"🌐 CopilotKit Server: http://{settings.A2A_HOST}:{settings.A2A_PORT}")
    print(f"💡 Frontend: cd ui/copilotkit && npm install && npm run dev")
    print(f"   (CopilotKit connects via HttpAgent to this server)")
    print(f"📊 Active Sessions: {session_manager.get_session_count()}")
    print(f"   Session IDs: {session_manager.list_session_ids()}")
    print("\n⚠️  Press Ctrl+C to shutdown gracefully\n")
    
    yield
    
    # Shutdown: Cleanup sub-agents
    print("\n🧹 Shutting down...")
    await cleanup_subagents()
    print("✅ Shutdown complete!")


# Create the FastAPI app with lifespan (matching the example pattern)
# Note: We'll initialize sub-agents in the lifespan context
app = create_app(agent_factory=create_supervisor_agent)

# Add lifespan events using FastAPI's lifespan parameter
# Since create_strands_app returns a FastAPI app, we need to wrap it
original_app = app

# Create a new app wrapper with lifespan
from fastapi import FastAPI as FastAPIApp

# We need to manually add startup/shutdown events since create_strands_app
# doesn't expose lifespan parameter. Let's use event handlers instead.
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    print("🚀 Starting DevOps Agent with CopilotKit...")
    await initialize_subagents()
    
    session_manager = app.state.session_manager
    print("\n" + "=" * 60)
    print("🎯 DevOps Supervisor Agent Server Running!")
    print("=" * 60)
    print(f"🌐 CopilotKit Server: http://{settings.A2A_HOST}:{settings.A2A_PORT}")
    print(f"💡 Frontend: cd ui/copilotkit && npm install && npm run dev")
    print(f"   (CopilotKit connects via HttpAgent to this server)")
    print(f"📊 Active Sessions: {session_manager.get_session_count()}")
    print(f"   Session IDs: {session_manager.list_session_ids()}")
    print("\n⚠️  Press Ctrl+C to shutdown gracefully\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    print("\n🧹 Shutting down...")
    await cleanup_subagents()
    print("✅ Shutdown complete!")


if __name__ == "__main__":
    import uvicorn
    
    # Run uvicorn server (matching the example pattern)
    uvicorn.run(
        "main:app",
        host=settings.A2A_HOST,
        port=settings.A2A_PORT,
        log_level="info",
        reload=False
    )

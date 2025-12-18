import asyncio
import logging
import signal
from core.config import settings
from core.server import AgentServer
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

async def main():
    """Main entry point"""
    print("🚀 Starting DevOps Agent...")
    
    # Initialize sub-agents
    await initialize_subagents()
    
    # Create server with supervisor factory
    server = AgentServer(agent_factory=create_supervisor_agent)
    
    # Start server
    await server.start()
    
    # Start email polling (if configured)
    # email_task = await start_email_polling(
    #     multi_session_manager=server.session_manager
    # )
    
    print("\n" + "=" * 60)
    print("🎯 DevOps Supervisor Agent Server Running!")
    print("=" * 60)
    print(f"🌐 API Server: http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"   POST /api/chat - Chat endpoint")
    print(f"   POST /api/chat/stream - Streaming chat (SSE)")
    print(f"   GET  /api/health - Health check")
    print(f"💡 UI Command: streamlit run ui/app.py")
    print(f"📊 Active Sessions: {server.session_manager.get_session_count()}")
    print(f"   Session IDs: {server.session_manager.list_session_ids()}")
    print("\n⚠️  Press Ctrl+C to shutdown gracefully\n")
    
    # Keep running until interrupted
    try:
        stop_event = asyncio.Event()
        
        def signal_handler():
            print("\nReceived shutdown signal...")
            stop_event.set()
            
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
            
        await stop_event.wait()
        
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)
    finally:
        print("\n🧹 Shutting down...")
        #await stop_email_polling()
        await server.stop()
        await cleanup_subagents()
        print("✅ Shutdown complete!")

if __name__ == "__main__":
    asyncio.run(main())

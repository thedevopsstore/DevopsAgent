import asyncio
import logging
import signal
from core.config import settings
from core.server import AgentServer
from agents.supervisor import create_supervisor_agent, initialize_subagents, cleanup_subagents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point"""
    print("🚀 Starting DevOps Agent...")
    
    # Initialize sub-agents
    await initialize_subagents()
    
    # Create server with supervisor factory
    server = AgentServer(agent_factory=create_supervisor_agent)
    
    # Start server
    await server.start()
    
    print("\n" + "=" * 60)
    print("🎯 DevOps Supervisor Agent Server Running!")
    print("=" * 60)
    print(f"🌐 A2A Server: http://{settings.A2A_HOST}:{settings.A2A_PORT}")
    print(f"💡 UI Command: streamlit run ui/app.py")
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
        await server.stop()
        await cleanup_subagents()
        print("✅ Shutdown complete!")

if __name__ == "__main__":
    asyncio.run(main())

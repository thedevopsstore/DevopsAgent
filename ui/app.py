"""
Streamlit UI for DevOps Supervisor Agent
Uses REST API to communicate with backend server
"""

import streamlit as st
import asyncio
import json
from datetime import datetime
from typing import Optional
import uuid
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Backend Configuration - Default URL
DEFAULT_BACKEND_URL = "http://localhost:9000"
DEFAULT_TIMEOUT = 300  # 5 minutes

def get_user_session_id() -> str:
    """Get or create a unique session ID for this Streamlit user"""
    if 'user_session_id' not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())
    return st.session_state.user_session_id

async def send_chat_message(message: str, backend_url: str, session_id: str = None) -> Optional[str]:
    """
    Send a message to the backend REST API
    
    Args:
        message: User message to send
        backend_url: Backend server URL
        session_id: Session ID for this user
        
    Returns:
        Response text from the agent, or None if error
    """
    try:
        # Use provided session_id or get from session state
        if session_id is None:
            session_id = get_user_session_id()
        
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                f"{backend_url}/api/chat",
                json={
                    "message": message,
                    "session_id": session_id
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
                    
    except httpx.ConnectError:
        return "Error: Could not connect to backend server. Make sure the server is running."
    except httpx.TimeoutException:
        return "Error: Request timed out. The agent may be processing a long-running task."
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return f"Error: HTTP {e.response.status_code} - {e.response.text}"
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        return f"Error: {str(e)}"

def send_message_to_backend(message: str, backend_url: str, session_id: str = None) -> Optional[str]:
    """
    Synchronous wrapper around async REST API client
    """
    try:
        # Run the async function in an event loop
        return asyncio.run(send_chat_message(message, backend_url, session_id))
    except Exception as e:
        logger.error(f"Error in sync wrapper: {e}", exc_info=True)
        return f"Error: {str(e)}"

def get_backend_url() -> str:
    """Get the backend URL from session state or default"""
    return st.session_state.get('backend_url', DEFAULT_BACKEND_URL)

async def check_backend_health_async(backend_url: str) -> bool:
    """Check if backend server is accessible"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{backend_url}/api/health")
            response.raise_for_status()
            return True
    except:
        return False

def check_backend_health(backend_url: str) -> bool:
    """Synchronous wrapper for health check"""
    try:
        return asyncio.run(check_backend_health_async(backend_url))
    except:
        return False

def initialize_session_state():
    """Initialize Streamlit session state"""
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    if 'backend_url' not in st.session_state:
        st.session_state.backend_url = DEFAULT_BACKEND_URL
    
    # Initialize user session ID (unique per Streamlit user session)
    if 'user_session_id' not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())

def display_agent_info():
    """Display DevOps Supervisor Agent information"""
    st.markdown("## <span style='color: #1E88E5;'>⚙️ DevOps Supervisor Agent</span>", unsafe_allow_html=True)
    
    backend_url = get_backend_url()
    # Check backend health
    backend_healthy = check_backend_health(backend_url)
    
    if backend_healthy:
        st.success("✅ **Connected to backend server (REST API)**")
        st.info("🤖 **Supervisor Agent** - Coordinates multiple specialized agents for infrastructure monitoring and management")
    else:
        st.error("❌ **Backend server not accessible**")
        st.warning("⚠️ Make sure `python main.py` is running")
        st.info(f"Trying to connect to: `{backend_url}`")
    
    st.write("**Capabilities:**")
    st.write("• Route queries to appropriate specialized agents")
    st.write("• AWS CloudWatch monitoring and troubleshooting")
    st.write("• Multi-agent coordination")
    st.write("• Intelligent query routing")
    
    return backend_healthy

def display_chat_interface():
    """Display chat interface for agent interaction"""
    backend_url = get_backend_url()
    backend_healthy = check_backend_health(backend_url)
    
    if not backend_healthy:
        st.warning("⚠️ Cannot connect to backend. Please start the server first.")
        st.code("python main.py", language="bash")
        return
    
    st.header("💬 Chat with Agent")
    
    # Display conversation history
    if st.session_state.conversation_history:
        for message in st.session_state.conversation_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if "timestamp" in message:
                    st.caption(f"🕒 {message['timestamp']}")
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to history
        user_message = {
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.conversation_history.append(user_message)
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_input)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Agent is thinking..."):
                try:
                    session_id = get_user_session_id()
                    response = send_message_to_backend(user_input, backend_url, session_id)
                    
                    if response:
                        st.write(response)
                        
                        # Add agent response to history
                        agent_message = {
                            "role": "assistant",
                            "content": response,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        st.session_state.conversation_history.append(agent_message)
                    else:
                        error_msg = "No response received from backend"
                        st.error(error_msg)
                        st.session_state.conversation_history.append({
                            "role": "assistant",
                            "content": error_msg,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    
                    # Add error to history
                    error_message = {
                        "role": "assistant",
                        "content": error_msg,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.conversation_history.append(error_message)

def display_sidebar():
    """Display sidebar with additional information"""
    with st.sidebar:
        st.header("ℹ️ Connection Info")
        
        # Backend URL configuration
        st.subheader("🔗 Backend Configuration")
        backend_url = st.text_input(
            "Backend URL",
            value=st.session_state.get('backend_url', DEFAULT_BACKEND_URL),
            key="backend_url_input"
        )
        st.session_state.backend_url = backend_url
        
        # Check connection
        if st.button("🔍 Check Connection"):
            if check_backend_health(backend_url):
                st.success("✅ Connected (REST API)")
            else:
                st.error("❌ Not connected")
        
        st.divider()
        
        st.subheader("📊 Chat Stats")
        st.write(f"**Messages:** {len(st.session_state.conversation_history)}")
        st.write(f"**Session ID:** `{get_user_session_id()[:16]}...`")
        st.caption("Each user has an isolated session with persistent conversation history")
        
        st.divider()
        
        # Clear conversation button
        if st.button("🗑️ Clear Conversation"):
            st.session_state.conversation_history = []
            st.rerun()
        
        # Export conversation button
        if st.session_state.conversation_history:
            if st.button("📥 Export Conversation"):
                conversation_data = {
                    "backend_url": st.session_state.backend_url,
                    "timestamp": datetime.now().isoformat(),
                    "messages": st.session_state.conversation_history
                }
                
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(conversation_data, indent=2),
                    file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        st.divider()
        
        st.subheader("📖 Instructions")
        st.write("1. Start the backend server:")
        st.code("python main.py", language="bash")
        st.write("2. The server will run on port 9000 by default")
        st.write("3. Chat with the agent using the interface below")
        st.write("4. Uses **REST API** for agent communication")

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="DevOps Supervisor Agent",
        page_icon="ui/gear_icon.svg",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("# <span style='color: #1E88E5;'>⚙️ DevOps Supervisor Agent</span>", unsafe_allow_html=True)
    st.markdown("Infrastructure monitoring and management with intelligent agent coordination (REST API)")
    
    # Initialize session state
    initialize_session_state()
    
    # Display sidebar
    display_sidebar()
    
    # Main content - show agent info
    display_agent_info()
    
    st.divider()
    
    # Chat interface
    display_chat_interface()

if __name__ == "__main__":
    main()

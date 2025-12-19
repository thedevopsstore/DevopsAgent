import asyncio
import logging
from core.config import settings

logger = logging.getLogger(__name__)

# Global task reference
email_polling_task = None

import time
import os
from pathlib import Path

async def email_polling_loop(multi_session_manager):
    """
    Background task that periodically prompts the supervisor to check for new emails.
    
    Uses ephemeral autonomous sessions so each poll is fresh with no history.
    Each poll creates a new session, processes emails, then cleans up.
    """
    logger.info(f"📧 Starting email polling loop (interval: {settings.EMAIL_POLL_INTERVAL}s)")
    
    while True:
        session_id = None
        session_file = None
        
        try:
            # Wait before each poll (first poll waits immediately, subsequent polls wait after previous completes)
            await asyncio.sleep(settings.EMAIL_POLL_INTERVAL)
            
            # Generate unique session ID for this poll
            session_id = f"{settings.AUTONOMOUS_SESSION_ID}-{int(time.time())}"
            session_file = Path(__file__).parent.parent / "sessions" / f"session_{session_id}" / "session.json"
            
            logger.info(f"📧 Triggering supervisor to check for new emails (Session: {session_id})...")
            
            # Get a fresh agent for this poll
            autonomous_agent = multi_session_manager.get_or_create_agent(session_id)
            
            email_check_prompt = (
                "Check for new emails or unread emails in the inbox. "
                "If there are any new emails in the inbox, read them, analyze what action is needed, "
                "and send response emails with the results."
            )
            
            # Call agent synchronously (agent() is sync, but we're in async context)
            # Use asyncio.to_thread() (Python 3.9+) - modern way to run sync code in async context
            # This prevents blocking the event loop during long-running agent operations
            response = await asyncio.to_thread(autonomous_agent, email_check_prompt)
            
            logger.info(f"📧 Email check completed. Response: {str(response)[:200]}...")
                
        except asyncio.CancelledError:
            logger.info("📧 Email polling loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in email polling loop: {e}", exc_info=True)
            # Don't sleep here - let the loop continue and sleep at the start of next iteration
        finally:
            # Cleanup: Remove session from memory (thread-safe via MultiSessionManager lock)
            if session_id:
                try:
                    # Note: FileSessionManager uses storage_dir, so session files are in session_{id}/session.json
                    # We can't easily delete the session file without accessing FileSessionManager internals
                    # The important cleanup is removing from memory to prevent accumulation
                    logger.debug(f"Cleaning up session: {session_id}")
                    
                    # Remove from memory dictionaries (note: this should ideally be thread-safe)
                    # MultiSessionManager uses a lock, but we're accessing internal dicts directly
                    # This is acceptable for cleanup, but ideally MultiSessionManager would have a remove_agent method
                    with multi_session_manager._lock:
                        if session_id in multi_session_manager.agents:
                            del multi_session_manager.agents[session_id]
                            logger.debug(f"Removed agent from memory: {session_id}")
                        if session_id in multi_session_manager.session_managers:
                            del multi_session_manager.session_managers[session_id]
                            logger.debug(f"Removed session manager from memory: {session_id}")
                            
                except Exception as cleanup_error:
                    logger.warning(f"Error during session cleanup for {session_id}: {cleanup_error}")

async def start_email_polling(multi_session_manager):
    """Start the background email polling task (optional - can be disabled)"""
    global email_polling_task
    
    logger.info(f"📧 Checking email polling configuration...")
    logger.info(f"   EMAIL_MCP_SERVER_URL: {settings.EMAIL_MCP_SERVER_URL}")
    logger.info(f"   EMAIL_POLL_INTERVAL: {settings.EMAIL_POLL_INTERVAL}")
    
    # Check if email MCP is configured
    if not settings.EMAIL_MCP_SERVER_URL:
        logger.warning("⚠️  EMAIL_MCP_SERVER_URL not configured, email polling disabled")
        return None
    
    # If EMAIL_POLL_INTERVAL is 0 or negative, skip polling (use external triggers only)
    if settings.EMAIL_POLL_INTERVAL <= 0:
        logger.info("📧 Email polling disabled (EMAIL_POLL_INTERVAL <= 0). Use external triggers (REST API) to check emails.")
        return None
    
    logger.info(f"📧 Starting email polling task...")
    email_polling_task = asyncio.create_task(email_polling_loop(multi_session_manager))
    logger.info(f"📧 Email polling started (interval: {settings.EMAIL_POLL_INTERVAL}s)")
    logger.info(f"   Using autonomous session: {settings.AUTONOMOUS_SESSION_ID}")
    logger.info("   You can also trigger email checks externally via REST API endpoint")
    return email_polling_task

async def stop_email_polling():
    """Stop the email polling task"""
    global email_polling_task
    
    if email_polling_task:
        logger.info("🛑 Stopping email polling...")
        email_polling_task.cancel()
        try:
            await email_polling_task
        except asyncio.CancelledError:
            pass
        email_polling_task = None
        logger.info("✅ Email polling stopped")

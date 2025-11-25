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
    """
    logger.info(f"📧 Starting email polling loop (interval: {settings.EMAIL_POLL_INTERVAL}s)")
    
    while True:
        session_id = f"{settings.AUTONOMOUS_SESSION_ID}-{int(time.time())}"
        session_file = Path(__file__).parent.parent / "sessions" / f"{session_id}.json"
        
        try:
            await asyncio.sleep(settings.EMAIL_POLL_INTERVAL)
            
            logger.debug(f"Triggering supervisor to check for new emails (Session: {session_id})...")
            
            # Get a fresh agent for this poll
            autonomous_agent = multi_session_manager.get_or_create_agent(session_id)
            
            email_check_prompt = (
                "Check for new emails or unread emails in the inbox. "
                "If there are any new emails in the inbox, read them, analyze what action is needed, "
                "and send response emails with the results."
            )
            
            try:
                response = autonomous_agent(email_check_prompt)
                logger.debug(f"Email check completed. Response: {str(response)[:200]}...")
            except Exception as e:
                logger.error(f"Error during email check: {e}", exc_info=True)
                
        except asyncio.CancelledError:
            logger.info("Email polling loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in email polling loop: {e}", exc_info=True)
            await asyncio.sleep(settings.EMAIL_POLL_INTERVAL)
        finally:
            # Cleanup: Remove the temporary session file
            if session_file.exists():
                try:
                    os.remove(session_file)
                    logger.debug(f"Cleaned up session file: {session_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup session file {session_file}: {e}")
            
            # Remove from memory if possible (optional, as MultiSessionManager keeps it)
            # Ideally MultiSessionManager should have a remove_agent method, but for now file cleanup is most important
            if session_id in multi_session_manager.agents:
                del multi_session_manager.agents[session_id]
            if session_id in multi_session_manager.session_managers:
                del multi_session_manager.session_managers[session_id]

async def start_email_polling(multi_session_manager):
    """Start the background email polling task (optional - can be disabled)"""
    global email_polling_task
    
    # Check if email MCP is configured
    if not settings.EMAIL_MCP_SERVER_URL:
        print("⚠️  EMAIL_MCP_SERVER_URL not configured, email polling disabled")
        return None
    
    # If EMAIL_POLL_INTERVAL is 0 or negative, skip polling (use external triggers only)
    if settings.EMAIL_POLL_INTERVAL <= 0:
        print("📧 Email polling disabled (EMAIL_POLL_INTERVAL <= 0). Use external triggers (A2A) to check emails.")
        return None
    
    email_polling_task = asyncio.create_task(email_polling_loop(multi_session_manager))
    print(f"📧 Email polling started (interval: {settings.EMAIL_POLL_INTERVAL}s)")
    print(f"   Using autonomous session: {settings.AUTONOMOUS_SESSION_ID}")
    print("   You can also trigger email checks externally via A2A endpoint")
    return email_polling_task

async def stop_email_polling():
    """Stop the email polling task"""
    global email_polling_task
    
    if email_polling_task:
        print("🛑 Stopping email polling...")
        email_polling_task.cancel()
        try:
            await email_polling_task
        except asyncio.CancelledError:
            pass
        email_polling_task = None
        print("✅ Email polling stopped")

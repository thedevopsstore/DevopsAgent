import asyncio
import logging
from core.config import settings

logger = logging.getLogger(__name__)

# Global task reference
email_polling_task = None

async def email_polling_loop(multi_session_manager):
    """
    Background task that periodically prompts the supervisor to check for new emails.
    
    Uses dedicated autonomous session (AUTONOMOUS_SESSION_ID) so email processing history
    is isolated from user sessions.
    
    The supervisor agent will autonomously:
    - Use list-mail-messages to check for new/unread emails
    - Read email content using get-mail-message
    - Analyze and delegate to worker agents
    - Send response emails using send-mail
    
    This is a clean, agentic approach where the supervisor handles everything.
    """
    logger.info(f"📧 Starting email polling loop (interval: {settings.EMAIL_POLL_INTERVAL}s)")
    logger.info(f"   Using autonomous session: {settings.AUTONOMOUS_SESSION_ID}")
    
    # Get the autonomous session agent
    autonomous_agent = multi_session_manager.get_or_create_agent(settings.AUTONOMOUS_SESSION_ID)
    
    while True:
        try:
            await asyncio.sleep(settings.EMAIL_POLL_INTERVAL)
            
            logger.debug("Triggering supervisor to check for new emails...")
            
            # Simple prompt - supervisor uses its MCP tools to handle everything
            # Uses dedicated autonomous session, so conversation history is isolated
            email_check_prompt = (
                "Check for new emails or unread emails in the inbox. "
                "If there are any new emails, read them, analyze what action is needed, "
                "delegate to the appropriate worker agent, and send response emails with the results."
            )
            
            # Let supervisor handle everything (agentic)
            # This uses the autonomous session, isolated from user sessions
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
            # Continue polling even if there's an error
            await asyncio.sleep(settings.EMAIL_POLL_INTERVAL)

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

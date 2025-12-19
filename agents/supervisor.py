import asyncio
import httpx
import logging
from uuid import uuid4
from strands import Agent, tool
from strands.models import BedrockModel
from agents.aws import AWSCloudWatchAgent
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, TextPart
from core.config import settings

logger = logging.getLogger(__name__)

# Initialize sub-agents
aws_agent = AWSCloudWatchAgent()
email_mcp_client = None

# A2A Client Tool for AWS Agent
class A2AAgentTool:
    """A2A client tool that connects to an agent via A2A protocol"""
    
    def __init__(self, agent_url: str, agent_name: str):
        self.agent_url = agent_url
        self.agent_name = agent_name
        self.agent_card = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the A2A client by fetching agent card"""
        if self._initialized:
            return
        
        try:
            # Just fetch the agent card during initialization
            async with httpx.AsyncClient(timeout=30) as httpx_client:
                resolver = A2ACardResolver(httpx_client=httpx_client, base_url=self.agent_url)
                self.agent_card = await resolver.get_agent_card()
                self._initialized = True
                logger.info(f"A2A client initialized for {self.agent_name} at {self.agent_url}")
        except Exception as e:
            logger.error(f"Failed to initialize A2A client for {self.agent_name}: {e}", exc_info=True)
            self._initialized = False
    
    @tool
    async def call_agent(self, message: str) -> str:
        """
        Send a message to the AWS CloudWatch Agent via A2A protocol.
        
        This tool connects to the AWS CloudWatch Agent which can:
        - List CloudWatch metrics for namespaces
        - Get metric statistics
        - Describe CloudWatch alarms
        - Filter and search CloudWatch logs
        
        Use this tool for any AWS CloudWatch-related queries, monitoring, or troubleshooting.

        Args:
            message: The query or request to send to the AWS CloudWatch Agent (e.g., "list all alarms", "check logs for errors", "get metrics for EC2")

        Returns:
            Response from the AWS CloudWatch Agent with the requested information or action results
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.agent_card:
            return f"Error: A2A agent card not available for {self.agent_name}"
        
        try:
            msg = Message(
                kind="message",
                role=Role.user,
                parts=[Part(TextPart(kind="text", text=message))],
                message_id=uuid4().hex,
            )
            
            # Create client for this request (httpx client must be created per request)
            async with httpx.AsyncClient(timeout=300) as httpx_client:
                config = ClientConfig(
                    httpx_client=httpx_client,
                    streaming=False,
                )
                factory = ClientFactory(config)
                client = factory.create(self.agent_card)
                
                async for event in client.send_message(msg):
                    if isinstance(event, Message):
                        response_text = ""
                        for part in event.parts:
                            if hasattr(part, 'text'):
                                response_text += part.text
                            elif hasattr(part, 'root') and hasattr(part.root, 'text'):
                                response_text += part.root.text
                            elif isinstance(part, dict) and 'text' in part:
                                response_text += part['text']
                        if response_text:
                            return response_text
                        return str(event)
                
                return f"No response received from {self.agent_name}"
        except Exception as e:
            return f"Error contacting {self.agent_name}: {str(e)}"

# Create A2A tool instance for AWS agent
aws_a2a_tool = A2AAgentTool(
    agent_url=f"http://{settings.A2A_HOST}:{settings.AWS_A2A_PORT}",
    agent_name="AWS CloudWatch Agent"
)

async def initialize_subagents():
    """Initialize all subagents"""
    global email_mcp_client
    
    logger.info("Initializing Subagents...")
    
    # Initialize AWS agent and start A2A server
    try:
        await aws_agent.initialize()
        await aws_agent.start_a2a_server()
        
        # Wait for server to start and retry connection
        max_retries = 5
        retry_delay = 1
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(retry_delay)
                await aws_a2a_tool.initialize()
                logger.info("AWS CloudWatch Agent A2A server and client initialized!")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Failed to connect to AWS A2A server (attempt {attempt + 1}/{max_retries}): {e}")
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to initialize AWS A2A client after {max_retries} attempts: {e}", exc_info=True)
                    raise
    except Exception as e:
        logger.error(f"Failed to initialize AWS A2A: {e}", exc_info=True)
    
    # Initialize Email MCP Client
    if settings.EMAIL_MCP_SERVER_URL:
        try:
            logger.info(f"📧 Connecting to Email MCP: {settings.EMAIL_MCP_SERVER_URL}")
            email_mcp_client = MCPClient(
                lambda: streamablehttp_client(
                    settings.EMAIL_MCP_SERVER_URL,
                    timeout=200,
                    sse_read_timeout=200
                )
            )
            email_mcp_client.__enter__()
            logger.info("✅ Email MCP Client initialized!")
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize Email MCP: {e}")
            email_mcp_client = None
    else:
        logger.info("📧 EMAIL_MCP_SERVER_URL not configured, email features disabled")
        email_mcp_client = None

async def cleanup_subagents():
    """Cleanup subagents"""
    global email_mcp_client
    
    # Stop AWS A2A server
    await aws_agent.cleanup()
    
    # Cleanup Email MCP Client
    if email_mcp_client:
        try:
            email_mcp_client.__exit__(None, None, None)
        except Exception as e:
            logger.warning(f"Error cleaning up Email MCP client: {e}")

def create_supervisor_agent(session_manager, conversation_manager=None) -> Agent:
    """Create the supervisor agent instance"""
    model = BedrockModel(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0.1,
    )
    
    tools = [aws_a2a_tool.call_agent]
    if email_mcp_client:
        tools.extend(email_mcp_client.list_tools_sync())
    
    prompt = """You are a DevOps Supervisor Agent.
    Your role is to coordinate specialized agents for infrastructure monitoring and management.
    
    Available Tools:
    - call_agent: Connects to the AWS CloudWatch Agent via A2A protocol. Use this for:
      * AWS CloudWatch metrics queries and analysis
      * CloudWatch log searches and filtering
      * CloudWatch alarm management and monitoring
      * AWS infrastructure troubleshooting
      Example: "call_agent('list all CloudWatch alarms')" or "call_agent('check logs for application errors')"
    - Email MCP Tools: For reading and sending emails.
    
    # Email Operations via MCP Server
    
    **Use the MS365 Email MCP Server for ALL email operations.**
    
    ## Tools
    
    **Reading**: `list-mail-messages` (default: unread Inbox only; set `unread_only=false` for all), `list-mail-folders` (get folder IDs), `list-mail-folder-messages` (specific folder), `get-mail-message` (full content by ID).
    
    **Sending**: `send-mail` (to, subject, body), `create-draft-email` (draft).
    
    **Managing**: `delete-mail-message` (by ID), `move-mail-message` (message ID + folder ID).
    
    ## Default Behavior
    
    `list-mail-messages` returns only **unread messages from Inbox** by default (minimizes tokens). Set `unread_only=false` for all messages. For other folders, use `list-mail-folders` first to get folder IDs.
    
    ## Workflow
    
    1. List messages → 2. Get full content with `get-mail-message` if needed → 3. Act using message IDs.
    
    Always delegate to the appropriate tool."""
    
    return Agent(
        model=model,
        tools=tools,
        system_prompt=prompt,
        session_manager=session_manager,
        conversation_manager=conversation_manager,  # Context window management
        description="DevOps Supervisor Agent that coordinates specialized agents for infrastructure monitoring and management."
    )

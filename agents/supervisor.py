from strands import Agent, tool
from strands.models import BedrockModel
from agents.aws import AWSCloudWatchAgent
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from core.config import settings

# Initialize sub-agents
aws_agent = AWSCloudWatchAgent()
email_mcp_client = None

async def initialize_subagents():
    """Initialize all subagents"""
    global email_mcp_client
    
    print("🚀 Initializing Subagents...")
    #await aws_agent.initialize()
    
    # if settings.EMAIL_MCP_SERVER_URL:
    #     try:
    #         print(f"📧 Connecting to Email MCP: {settings.EMAIL_MCP_SERVER_URL}")
    #         email_mcp_client = MCPClient(
    #             lambda: streamablehttp_client(
    #                 settings.EMAIL_MCP_SERVER_URL,
    #                 timeout=200,
    #                 sse_read_timeout=200
    #             )
    #         )
    #         email_mcp_client.__enter__()
    #         print("✅ Email MCP Client initialized!")
    #     except Exception as e:
    #         print(f"⚠️  Failed to initialize Email MCP: {e}")
    #         email_mcp_client = None

async def cleanup_subagents():
    """Cleanup subagents"""
    global email_mcp_client
    
    # await aws_agent.cleanup()
    # if email_mcp_client:
    #     email_mcp_client.__exit__(None, None, None)

@tool
async def aws_cloudwatch_tool(query: str) -> str:
    """Handle AWS CloudWatch-related queries"""
    return await aws_agent.run_conversation(query)

def create_supervisor_agent(session_manager, conversation_manager=None) -> Agent:
    """Create the supervisor agent instance"""
    model = BedrockModel(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0.1,
    )
    
    tools = [aws_cloudwatch_tool]
    if email_mcp_client:
        tools.extend(email_mcp_client.list_tools_sync())
    
    prompt = """You are a DevOps Supervisor Agent.
    Your role is to coordinate specialized agents for infrastructure monitoring and management.
    
    Available Tools:
    - aws_cloudwatch_tool: For AWS metrics and logs.
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

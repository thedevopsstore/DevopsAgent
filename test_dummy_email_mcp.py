"""
Dummy Email MCP Server for Local Testing
Simulates an email MCP server that responds to list-mail-messages and other email operations
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dummy Email MCP Server")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory email storage for testing
fake_emails = [
    {
        "id": "email-1",
        "subject": "Test Email 1",
        "from": "test@example.com",
        "to": "devops@example.com",
        "body": "This is a test email for email polling.",
        "unread": True,
        "receivedDateTime": "2024-01-01T10:00:00Z"
    },
    {
        "id": "email-2",
        "subject": "AWS Alert - High CPU",
        "from": "alerts@aws.com",
        "to": "devops@example.com",
        "body": "CPU usage is above 90% on instance i-12345",
        "unread": True,
        "receivedDateTime": "2024-01-01T11:00:00Z"
    }
]

# MCP uses JSON-RPC 2.0 format
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[Dict[str, Any]] = None

@app.post("/message")
async def handle_mcp_message(request: dict):
    """Handle MCP protocol messages (JSON-RPC 2.0 format)"""
    logger.info(f"Received MCP request: {request}")
    
    # Extract JSON-RPC fields
    jsonrpc = request.get("jsonrpc", "2.0")
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    logger.info(f"  Method: {method}, ID: {request_id}, Params: {params}")
    
    try:
        if method == "initialize":
            # MCP initialize handshake
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "dummy-email-mcp-server",
                    "version": "1.0.0"
                }
            }
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        
        elif method == "initialized":
            # MCP initialized notification (no response needed, but we'll log it)
            logger.info("MCP client initialized notification received")
            # Notifications don't require a response, but FastAPI needs one
            return {"status": "ok"}
        
        elif method == "tools/list":
            # Return available email tools
            result = {
                "tools": [
                    {
                        "name": "list-mail-messages",
                        "description": "List email messages from inbox",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "unread_only": {"type": "boolean", "default": True},
                                "folder_id": {"type": "string", "default": "inbox"}
                            }
                        }
                    },
                    {
                        "name": "get-mail-message",
                        "description": "Get full content of an email by ID",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message_id": {"type": "string", "required": True}
                            }
                        }
                    },
                    {
                        "name": "send-mail",
                        "description": "Send an email",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "to": {"type": "string", "required": True},
                                "subject": {"type": "string", "required": True},
                                "body": {"type": "string", "required": True}
                            }
                        }
                    }
                ]
            }
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        
        elif method == "tools/call":
            tool_name = params.get("name") if params else None
            arguments = params.get("arguments", {}) if params else {}
            
            if tool_name == "list-mail-messages":
                unread_only = arguments.get("unread_only", True)
                folder_id = arguments.get("folder_id", "inbox")
                
                # Filter emails
                filtered_emails = fake_emails
                if unread_only:
                    filtered_emails = [e for e in fake_emails if e.get("unread", False)]
                
                result = {
                    "messages": [
                        {
                            "id": email["id"],
                            "subject": email["subject"],
                            "from": email["from"],
                            "to": email["to"],
                            "receivedDateTime": email["receivedDateTime"],
                            "isRead": not email["unread"]
                        }
                        for email in filtered_emails
                    ]
                }
                logger.info(f"Returning {len(result['messages'])} emails")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            
            elif tool_name == "get-mail-message":
                message_id = arguments.get("message_id")
                email = next((e for e in fake_emails if e["id"] == message_id), None)
                
                if not email:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32602,
                            "message": f"Email {message_id} not found"
                        }
                    }
                
                result = {
                    "id": email["id"],
                    "subject": email["subject"],
                    "from": email["from"],
                    "to": email["to"],
                    "body": email["body"],
                    "receivedDateTime": email["receivedDateTime"],
                    "isRead": not email["unread"]
                }
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            
            elif tool_name == "send-mail":
                to = arguments.get("to")
                subject = arguments.get("subject")
                body = arguments.get("body")
                
                logger.info(f"📧 Sending email to {to}: {subject}")
                result = {"success": True, "message": "Email sent successfully"}
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown method: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": request_id if 'request_id' in locals() else None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "emails_count": len(fake_emails)}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Dummy Email MCP Server",
        "description": "Test server for email polling",
        "endpoints": {
            "mcp": "/message",
            "health": "/health"
        },
        "fake_emails": len(fake_emails)
    }

if __name__ == "__main__":
    print("🚀 Starting Dummy Email MCP Server...")
    print("   URL: http://localhost:8100/message")
    print("   Health: http://localhost:8100/health")
    print("\n📧 Fake emails available:")
    for email in fake_emails:
        print(f"   - {email['subject']} ({'unread' if email['unread'] else 'read'})")
    print("\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8100, log_level="info")


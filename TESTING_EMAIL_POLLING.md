# Testing Email Polling Locally

## Issue
Email polling is not starting even though:
- Email MCP client is initialized ✅
- Configuration is set (EMAIL_MCP_SERVER_URL, EMAIL_POLL_INTERVAL) ✅
- But polling start messages are not appearing ❌

## Debugging Steps

### 1. Check Configuration Values
After you see "Email MCP Client initialized", you should see:
```
============================================================
📧 Checking email polling configuration...
   EMAIL_MCP_SERVER_URL: http://localhost:8100/message
   EMAIL_POLL_INTERVAL: 300
```

**If you DON'T see this**, it means `start_email_polling()` is not being called or is failing silently.

### 2. Check What You Should See

**Expected sequence:**
1. ✅ Email MCP Client initialized
2. ✅ Session created (default)
3. ✅ FastAPI server started
4. ❓ **📧 Checking email polling configuration...** ← Should appear here
5. ❓ **✅ Email polling started** ← Should appear here

### 3. Test with Dummy MCP Server

I've created `test_dummy_email_mcp.py` - a simple MCP server for testing.

**Start the dummy server:**
```bash
python test_dummy_email_mcp.py
```

This will start a server on `http://localhost:8100/message`

**Note:** The dummy server may not fully implement the MCP protocol (which uses SSE/streaming). The real MCP server format might be different. But it should at least allow the MCP client to connect.

### 4. Check Logs

Look for these messages in order:
1. `📧 Connecting to Email MCP: http://localhost:8100/message`
2. `✅ Email MCP Client initialized!`
3. `📁 Created new session: default`
4. `🚀 Starting FastAPI server...`
5. **`📧 Checking email polling configuration...`** ← This should appear
6. **`✅ Email polling started`** ← This should appear

If step 5 doesn't appear, `start_email_polling()` is not being called or is returning early.

### 5. Manual Test

You can manually trigger an email check via REST API:
```bash
curl -X POST http://localhost:9000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Check for new emails",
    "session_id": "test-session"
  }'
```

This will test if the agent can use email tools even if polling isn't working.

## Next Steps

1. **Check if `start_email_polling()` is actually being called** - Add a print at the very start of the function
2. **Check if it's returning None early** - The new logging will show why
3. **Verify MCP client is actually initialized** - Check if `email_mcp_client` is not None in supervisor.py


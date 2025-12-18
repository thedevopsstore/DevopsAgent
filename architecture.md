# DevOps Agent Architecture & Design Document

## 1. System Overview
The **DevOps Supervisor Agent** is an intelligent, multi-agent system designed to assist with infrastructure monitoring and management. It uses a **Supervisor-Worker** pattern where a central Supervisor agent coordinates specialized sub-agents (AWS CloudWatch, Email) to fulfill user requests.

The system is built on the **Strands** framework and uses **CopilotKit** with **ag-ui-strands** for native integration between the frontend UI and the backend agent server. The supervisor agent communicates directly with sub-agents (no A2A protocol between agents). It supports both interactive chat sessions and autonomous background operations (email polling).

## 2. High-Level Architecture

```mermaid
graph TD
    User[User] <--> UI[CopilotKit UI]
    UI <-->|"AG-UI Protocol via HttpAgent"| Server[CopilotKit Server]
    
    User2[User] -.->|"Legacy"| Streamlit[Streamlit UI]
    Streamlit -.->|"A2A Protocol"| Server2[A2A Server - Legacy]
    
    subgraph "Backend (Python/Strands)"
        Server -->|"ag-ui-strands"| Supervisor[Supervisor Agent]
        
        Supervisor -->|"A2A Protocol"| AWS_A2A[AWS A2A Server]
        AWS_A2A --> AWS[AWS CloudWatch Agent]
        Supervisor -->|"Direct Call"| Email[Email MCP Client]
        
        AWS -->|Boto3| CloudWatch[AWS CloudWatch API]
        AWS -->|Boto3| Logs[AWS CloudWatch Logs]
        
        Email -->|MCP| MS365[MS365 Email Server]
        
        Polling[Email Polling Loop] -.->|Triggers| Supervisor
    end
    
    subgraph "Data Persistence"
        Server --> Sessions[MultiSessionManager]
        Sessions --> Disk["/app/sessions/*.json"]
    end
```

## 3. Core Components

### 3.1. Frontend
- **Streamlit UI** (`ui/app.py`): Legacy Streamlit interface (can be used alongside CopilotKit)
- **CopilotKit UI** (`ui/copilotkit/`): Modern React/Next.js frontend using CopilotKit
    - **Path**: `ui/copilotkit/`
    - **Role**: User interface for chatting with the agent via CopilotKit components
    - **Key Features**:
        - **CopilotKit Runtime**: Uses `CopilotRuntime` with `HttpAgent` to connect to backend
        - **AG-UI Protocol**: Communicates with backend server via AG-UI protocol (port 9000)
        - **CopilotKit Components**: Uses `CopilotSidebar` for chat interface
        - **Native Integration**: Direct connection to Strands agents via CopilotKit

### 3.2. Backend Server
- **Path**: `core/copilotkit_server.py` (new), `core/server.py` (legacy A2A)
- **Role**: Hosts the agents and exposes them via CopilotKit/AG-UI protocol.
- **Key Features**:
    - **CopilotKit Server**: Uses `ag-ui-strands` to create FastAPI app that exposes Strands agents
    - **MultiSessionManager**: Manages the lifecycle of agent instances per session
    - **SummarizingConversationManager**: Automatically summarizes conversation history to manage context window efficiency (keep last 10 messages, summarize 40%)
    - **AG-UI Protocol**: Exposes agents via AG-UI protocol for CopilotKit's HttpAgent to connect

### 3.3. Agents
- **Supervisor Agent** (`agents/supervisor.py`):
    - **Model**: Claude 3.5 Haiku (via Bedrock).
    - **Role**: Router/Orchestrator. Analyzes user intent and calls the appropriate tool.
    - **Tools**: 
        - `call_agent`: Connects to AWS Agent via A2A protocol.
        - `list-mail-messages`, `send-mail`, etc.: Direct MCP tools for email.
    - **Communication**: Uses A2A protocol to communicate with sub-agents (AWS CloudWatch Agent).
- **AWS CloudWatch Agent** (`agents/aws.py`):
    - **Model**: Claude 3.5 Haiku.
    - **Role**: Specialist. Executes specific AWS commands.
    - **Tools**: `list_metrics`, `get_metric_statistics`, `describe_alarms`, `filter_log_events`.
    - **Communication**: Exposed via A2A server (port 9001), called by supervisor via A2A protocol.

### 3.4. Autonomous Services
- **Email Polling** (`core/email_polling.py`):
    - **Role**: Periodically checks for new emails to trigger autonomous actions.
    - **Mechanism**: Runs an async loop that creates a **fresh, ephemeral session** for each poll.
    - **Context**: Uses `AUTONOMOUS_SESSION_ID-<timestamp>` to ensure no context is carried over between polls (stateless execution).
    - **Cleanup**: Automatically deletes session files after each poll to prevent disk clutter.

### 3.5. Configuration
- **Path**: `core/config.py`
- **Library**: `pydantic-settings`.
- **Source**: Environment variables (`.env` or system env).
- **Key Settings**: `A2A_HOST`, `A2A_PORT`, `AWS_REGION`, `EMAIL_MCP_SERVER_URL`, `EMAIL_POLL_INTERVAL`.

## 4. Data Flow

### 4.1. User Interaction
1.  **User Input**: User types a message in CopilotKit UI.
2.  **UI Processing**:
    - CopilotKit Runtime receives the message.
    - `HttpAgent` sends message to `http://localhost:9000/copilotkit` via AG-UI protocol.
3.  **Server Routing**:
    - CopilotKit server (FastAPI) receives the request.
    - `MultiSessionManager` retrieves or creates the agent for that session (from headers/query params).
4.  **Agent Execution**:
    - **Supervisor** receives the message.
    - Supervisor plans and executes tools (AWS, Email).
    - For AWS queries: Supervisor uses A2A client to call AWS Agent's A2A server.
    - Results are returned up the chain via A2A protocol.
5.  **Response**:
    - Agent generates a text response (streamed).
    - Server streams response via AG-UI protocol.
    - CopilotKit UI receives and displays the streamed response.

### 4.2. Autonomous Email Polling
1.  **Trigger**: `email_polling_loop` wakes up (default: 60s).
2.  **Session Creation**: Creates a unique session ID `autonomous-<timestamp>`.
3.  **Prompt**: Sends a system prompt: "Check for new emails...".
4.  **Execution**: Supervisor uses `list-mail-messages` tool.
5.  **Action**: If emails found, Supervisor reads content and takes action (e.g., check AWS metrics, reply).
6.  **Cleanup**: Session file is deleted.

## 5. Deployment & Logging

### 5.1. Docker
- **Base Image**: Python 3.12-slim.
- **Startup**: `start_services.sh` handles the sequence:
    1.  Start Backend (`main.py`) in background.
    2.  Wait for port 9000.
    3.  Start Frontend (`streamlit run ui/app.py`).
- **Logging**:
    - Backend logs are piped to **both** stdout (for `docker logs`) and `/app/logs/backend.log` (for persistence).
    - `strands` library logging is set to `DEBUG` to show agent thought process.

### 5.2. Kubernetes (Planned)
- Designed to run as a single Pod containing both containers (or single container with supervisor process).
- **Identity**: Uses AWS Pod Identity for `boto3` credentials (no hardcoded keys).

## 6. Directory Structure

```text
devops_agent/
├── agents/                 # Agent definitions
│   ├── aws.py              # AWS Specialist
│   ├── aws_mcp_agent.py    # (Legacy/Alternative)
│   └── supervisor.py       # Supervisor Agent
├── core/                   # Core infrastructure
│   ├── config.py           # Settings (Pydantic)
│   ├── email_polling.py    # Autonomous polling logic
│   └── server.py           # A2A Server & Session logic
├── ui/                     # Frontend
│   ├── app.py              # Streamlit App (legacy)
│   ├── copilotkit/         # CopilotKit React/Next.js frontend
│   │   ├── app/            # Next.js app directory
│   │   ├── package.json    # Frontend dependencies
│   │   └── ...
│   └── gear_icon.svg       # UI Asset
├── sessions/               # Persisted session data (JSON)
├── main.py                 # Entry point
├── start_services.sh       # Docker startup script
├── pyproject.toml          # Dependencies (UV)
└── Dockerfile              # Container config
```

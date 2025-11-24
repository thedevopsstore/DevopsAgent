# DevOps Agent Architecture & Design Document

## 1. System Overview
The **DevOps Supervisor Agent** is an intelligent, multi-agent system designed to assist with infrastructure monitoring and management. It uses a **Supervisor-Worker** pattern where a central Supervisor agent coordinates specialized sub-agents (currently AWS CloudWatch) to fulfill user requests.

The system is built on the **Strands** framework and uses the **Agent-to-Agent (A2A)** protocol for standardized communication between the frontend UI and the backend agent server.

## 2. High-Level Architecture

```mermaid
graph TD
    User[User] <--> UI[Streamlit UI]
    UI <-->|"A2A Protocol (JSON-RPC)"| Server[Agent Server]
    
    subgraph "Backend (Python/Strands)"
        Server --> Supervisor[Supervisor Agent]
        Supervisor -->|Delegates| AWS[AWS CloudWatch Agent]
        Supervisor -->|Delegates| Email["Email Agent (Future)"]"
        
        AWS -->|Boto3| CloudWatch[AWS CloudWatch API]
        AWS -->|Boto3| Logs[AWS CloudWatch Logs]
    end
    
    subgraph "Data Persistence"
        Server --> Sessions[File Session Manager]
        Sessions --> Disk[./sessions/*.json]
    end
```

## 3. Core Components

### 3.1. Frontend (Streamlit UI)
- **Path**: `ui/app.py`
- **Role**: User interface for chatting with the agent.
- **Key Features**:
    - **A2A Client**: Uses `a2a-sdk` to communicate with the backend.
    - **Caching**: Caches the Agent Card using `@st.cache_resource` to minimize network overhead.
    - **Session Management**: Generates a unique `user_session_id` for each browser tab/user.
    - **Theming**: Custom DevOps-themed UI (Blue Gear icon).

### 3.2. Backend Server
- **Path**: `core/server.py`
- **Role**: Hosts the agents and exposes them via the A2A protocol.
- **Key Features**:
    - **A2AServer**: Uses `strands.multiagent.a2a.A2AServer` to provide JSON-RPC endpoints.
    - **SessionAwareAgent**: A wrapper that routes incoming requests to the correct agent instance based on `session_id`.
    - **MultiSessionManager**: Manages the lifecycle of agent instances per session.
    - **Optimization**: Pre-compiled regex patterns for efficient session ID extraction.

### 3.3. Agents
- **Supervisor Agent** (`agents/supervisor.py`):
    - **Model**: Claude 3.5 Haiku (via Bedrock).
    - **Role**: Router/Orchestrator. Analyzes user intent and calls the appropriate tool.
    - **Tools**: `aws_cloudwatch_tool`.
- **AWS CloudWatch Agent** (`agents/aws.py`):
    - **Model**: Claude 3.5 Haiku.
    - **Role**: Specialist. Executes specific AWS commands.
    - **Tools**: `list_metrics`, `get_metric_statistics`, `describe_alarms`, `filter_log_events`.
    - **Implementation**: Tools are defined as instance methods for better encapsulation.

### 3.4. Configuration
- **Path**: `core/config.py`
- **Library**: `pydantic-settings`.
- **Source**: Environment variables (`.env` or system env).
- **Key Settings**: `A2A_HOST`, `A2A_PORT`, `AWS_REGION`.

## 4. Data Flow

1.  **User Input**: User types a message in Streamlit.
2.  **UI Processing**:
    - UI appends `session_id` to the message text.
    - UI sends message to `http://localhost:9000/` via A2A client.
3.  **Server Routing**:
    - `A2AServer` receives the request.
    - `SessionAwareAgent` extracts `session_id` from the message.
    - `MultiSessionManager` retrieves or creates the agent for that session.
4.  **Agent Execution**:
    - **Supervisor** receives the message.
    - If task requires AWS, Supervisor calls `aws_cloudwatch_tool`.
    - **AWS Agent** executes the tool (e.g., `boto3.client('cloudwatch').list_metrics()`).
    - Results are returned up the chain.
5.  **Response**:
    - Agent generates a text response.
    - Server wraps it in an A2A `Task` object.
    - UI receives the `Task`, extracts the text from `artifacts`, and displays it.

## 5. Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.12+ | Core logic |
| **Framework** | Strands | Agent framework |
| **Protocol** | A2A (Agent-to-Agent) | Standardized communication |
| **Frontend** | Streamlit | User Interface |
| **Server** | FastAPI / Uvicorn | HTTP Server (underlying A2AServer) |
| **Package Mgr** | UV | Fast dependency management |
| **Container** | Docker | Deployment |
| **AWS SDK** | Boto3 | Cloud interaction |
| **LLM** | Anthropic Claude 3.5 | Intelligence (via Bedrock) |

## 6. Directory Structure

```text
devops_agent/
├── agents/                 # Agent definitions
│   ├── aws.py
│   └── supervisor.py
├── core/                   # Core infrastructure
│   ├── config.py           # Settings
│   └── server.py           # Server & Session logic
├── ui/                     # Frontend
│   └── app.py
├── sessions/               # Persisted session data (JSON)
├── main.py                 # Entry point
├── pyproject.toml          # Dependencies (UV)
└── Dockerfile              # Container config
```

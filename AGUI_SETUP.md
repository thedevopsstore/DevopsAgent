# CopilotKit / A2A Protocol Setup Guide

This guide explains how to use the CopilotKit frontend with native A2A protocol support.

## Architecture

```
Frontend (CopilotKit) → A2A Server (port 9000) → Strands Agent
```

**Note:** CopilotKit has native A2A protocol support, so no bridge server is needed!

## Quick Start

### 1. Install Backend Dependencies

```bash
# Install Python dependencies (includes FastAPI, uvicorn)
pip install -e .
# or
uv pip install -e .
```

### 2. Install Frontend Dependencies

```bash
cd ui/copilotkit
npm install
```

### 3. Start the Backend

```bash
# This starts both A2A server (port 9000) and AG-UI server (port 8000)
python main.py
```

You should see:
```
🌐 A2A Server: http://127.0.0.1:9000
```

### 4. Start the Frontend

```bash
cd ui/copilotkit
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## What Changed

- **Replaced Streamlit UI** with React/Next.js + CopilotKit
- **Direct A2A Connection**: CopilotKit connects directly to A2A server (no bridge needed)
- **Simple Frontend** (`ui/copilotkit/`) with minimal CopilotKit integration

## Configuration

Edit `core/config.py` to change ports:
- `A2A_PORT`: A2A server port (default: 9000)

## Features

- ✅ Chat interface via CopilotKit sidebar
- ✅ Streaming responses
- ✅ Session management (via A2A backend)
- ✅ Simple and minimal implementation

## Next Steps

You can extend the frontend with:
- Tool-based Generative UI
- Shared state
- Human-in-the-loop features
- Custom components

See [CopilotKit docs](https://docs.copilotkit.ai) for more features.


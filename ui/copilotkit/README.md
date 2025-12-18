# DevOps Agent Frontend (CopilotKit)

Simple React/Next.js frontend using CopilotKit to interact with the DevOps Supervisor Agent.

Located in `ui/copilotkit/` to match the project architecture.

## Setup

1. Install dependencies:
```bash
cd ui/copilotkit
npm install
```

2. Set environment variable (optional, defaults to http://localhost:9000):
```bash
export NEXT_PUBLIC_A2A_SERVER_URL=http://localhost:9000
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## How it works

- CopilotKit connects **directly** to the A2A server using native A2A protocol support
- No bridge server needed - CopilotKit understands A2A protocol natively
- The A2A server (port 9000) connects to your Strands agent

Make sure the backend server is running:
- A2A server: `python main.py`


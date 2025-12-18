import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

// Supervisor Agent URL (CopilotKit server)
const SUPERVISOR_AGENT_URL = process.env.SUPERVISOR_AGENT_URL || "http://localhost:9000";

// The supervisor agent - accessed via HttpAgent
// This connects to the FastAPI server that exposes the Strands agent via AG-UI protocol
const supervisorAgent = new HttpAgent({
  url: SUPERVISOR_AGENT_URL,
});

const serviceAdapter = new ExperimentalEmptyAdapter();

// CopilotKit runtime connects frontend to agent system
const runtime = new CopilotRuntime({
  agents: {
    devopsAgent: supervisorAgent, // Must match agent prop in <CopilotKit agent="devopsAgent">
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};


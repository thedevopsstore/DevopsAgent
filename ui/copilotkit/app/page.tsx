"use client";

import { useEffect, useState } from "react";
import { CopilotSidebar, CopilotKitCSSProperties } from "@copilotkit/react-ui";
import {
  useDefaultTool,
  useRenderToolCall,
  useFrontendTool,
} from "@copilotkit/react-core";
import { DefaultToolComponent } from "@/components/default-tool-ui";
import { AWSCloudWatchCard } from "@/components/aws-cloudwatch-card";

export default function CopilotKitPage() {
  const [themeColor, setThemeColor] = useState("#6366f1");

  // Frontend tool to change theme color
  useFrontendTool({
    name: "set_theme_color",
    parameters: [
      {
        name: "theme_color",
        description: "The theme color to set. Make sure to pick nice colors.",
        required: true,
      },
    ],
    handler({ theme_color }) {
      setThemeColor(theme_color);
    },
  });

  return (
    <main
      style={
        { "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties
      }
    >
      <CopilotSidebar
        clickOutsideToClose={false}
        defaultOpen={true}
        labels={{
          title: "DevOps Supervisor Agent",
          initial: "👋 Hi! I'm your DevOps Supervisor Agent. I can help you monitor AWS CloudWatch, manage infrastructure, and coordinate with specialized agents. How can I help you today?",
        }}
        suggestions={[
          {
            title: "AWS Monitoring",
            message: "List all CloudWatch alarms",
          },
          {
            title: "Log Analysis",
            message: "Check logs for errors in my application",
          },
          {
            title: "Metrics",
            message: "Get metrics for EC2 instances",
          },
          {
            title: "Theme",
            message: "Set the theme to orange",
          },
        ]}
      >
        {/* Wrapping your content in the sidebar pushes it to the side*/}
        <YourMainContent themeColor={themeColor} />
      </CopilotSidebar>
    </main>
  );
}

function YourMainContent({ themeColor }: { themeColor: string }) {
  // Render AWS CloudWatch tool calls with custom UI
  useRenderToolCall(
    {
      name: "call_agent",
      parameters: [
        {
          name: "message",
          description: "The query or request to send to the AWS CloudWatch Agent",
          required: true,
        },
      ],
      render: (props) => (
        <AWSCloudWatchCard themeColor={themeColor} {...props} />
      ),
    },
    [themeColor],
  );

  // Default Generative UI for other backend tools
  useDefaultTool(
    {
      render: (props) => (
        <DefaultToolComponent themeColor={themeColor} {...props} />
      ),
    },
    [themeColor],
  );

  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="h-screen flex justify-center items-start pt-12 flex-col transition-colors duration-300 overflow-y-auto"
    >
      <div className="bg-white/20 backdrop-blur-md p-8 rounded-2xl shadow-xl max-w-4xl w-full mx-auto mb-8">
        <div className="flex items-center gap-4 mb-6">
          <div className="bg-white/30 p-3 rounded-xl">
            <svg
              className="w-8 h-8 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-4xl font-bold text-white mb-1">
              DevOps Supervisor Agent
            </h1>
            <p className="text-white/90 text-sm">
              Infrastructure monitoring and management powered by AI agents
            </p>
          </div>
        </div>

        <hr className="border-white/20 my-6" />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-white/15 p-4 rounded-xl text-white">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              AWS CloudWatch
            </h3>
            <p className="text-sm text-white/80">
              Monitor metrics, logs, and alarms in real-time
            </p>
          </div>

          <div className="bg-white/15 p-4 rounded-xl text-white">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
              Multi-Agent Coordination
            </h3>
            <p className="text-sm text-white/80">
              Coordinate specialized agents via A2A protocol
            </p>
          </div>

          <div className="bg-white/15 p-4 rounded-xl text-white">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              Real-time Monitoring
            </h3>
            <p className="text-sm text-white/80">
              Track infrastructure health and performance
            </p>
          </div>

          <div className="bg-white/15 p-4 rounded-xl text-white">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
              Email Integration
            </h3>
            <p className="text-sm text-white/80">
              Autonomous operations via email triggers
            </p>
          </div>
        </div>

        <div className="bg-white/10 p-4 rounded-lg border border-white/20">
          <p className="text-white/90 text-sm text-center">
            💡 <strong>Tip:</strong> Use the chat sidebar to interact with the agent. 
            AWS CloudWatch queries will be rendered with custom UI components on this page!
          </p>
        </div>
      </div>

      {/* This is where tool call results will be rendered */}
      <div className="w-full max-w-4xl mx-auto px-4 pb-8">
        {/* Tool call results appear here via useRenderToolCall */}
      </div>
    </div>
  );
}


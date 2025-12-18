import { CatchAllActionRenderProps } from "@copilotkit/react-core";

interface AWSCloudWatchCardProps extends CatchAllActionRenderProps {
  themeColor?: string;
}

export function AWSCloudWatchCard({
  name,
  args,
  status,
  result,
  themeColor = "#6366f1",
}: AWSCloudWatchCardProps) {
  const getStatusColor = () => {
    switch (status) {
      case "executing":
      case "inProgress":
        return "bg-blue-500/20 text-blue-700 border-blue-400/30";
      case "complete":
        return "bg-green-500/20 text-green-700 border-green-400/30";
      default:
        return "bg-gray-500/20 text-gray-700 border-gray-400/30";
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case "executing":
      case "inProgress":
        return (
          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        );
      case "complete":
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div
      style={{ borderColor: themeColor }}
      className="rounded-xl shadow-lg mt-6 mb-4 max-w-2xl w-full border-2 bg-white/95 backdrop-blur-sm"
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              style={{ backgroundColor: themeColor }}
              className="p-2 rounded-lg"
            >
              <svg
                className="w-6 h-6 text-white"
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
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-800">AWS CloudWatch</h3>
              <p className="text-sm text-gray-500">{name}</p>
            </div>
          </div>
          <span
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${getStatusColor()}`}
          >
            {getStatusIcon()}
            {status}
          </span>
        </div>

        {/* Arguments */}
        {args && Object.keys(args).length > 0 && (
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs font-semibold text-gray-600 mb-2">Query:</p>
            <p className="text-sm text-gray-800 font-mono">
              {typeof args === "string" ? args : JSON.stringify(args, null, 2)}
            </p>
          </div>
        )}

        {/* Result */}
        {result && status === "complete" && (
          <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
            <p className="text-xs font-semibold text-green-700 mb-2">Result:</p>
            <pre className="text-sm text-green-800 font-mono whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
              {typeof result === "string"
                ? result
                : JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}

        {/* Loading state */}
        {status !== "complete" && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-700 flex items-center gap-2">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Processing AWS CloudWatch request...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}


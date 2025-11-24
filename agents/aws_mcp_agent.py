import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from typing import Dict, Any, Optional

class AWSCloudWatchAgent:
    """
    Agent specialized in AWS CloudWatch operations.
    Uses boto3 to interact with AWS CloudWatch.
    """
    
    def __init__(self):
        self._initialized = False
        self.agent = None
        self.cloudwatch = None
        self.logs = None

    async def initialize(self):
        """Initialize the agent and AWS clients"""
        if self._initialized:
            return

        # Initialize AWS clients
        # Note: This assumes AWS credentials are configured in the environment
        # or via ~/.aws/credentials
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
            self.logs = boto3.client('logs', region_name='us-east-1')
        except Exception as e:
            print(f"Warning: Could not initialize AWS clients: {e}")
            # We continue, but tools will fail if called
        
        # Create the model
        model = BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0,
        )

        # Define tools
        @tool
        def list_metrics(namespace: str) -> str:
            """List CloudWatch metrics for a given namespace"""
            if not self.cloudwatch:
                return "Error: AWS CloudWatch client not available"
            try:
                response = self.cloudwatch.list_metrics(Namespace=namespace)
                return str(response.get('Metrics', []))
            except Exception as e:
                return f"Error listing metrics: {str(e)}"

        @tool
        def get_metric_statistics(namespace: str, metric_name: str, start_time: str, end_time: str, period: int = 300, stat: str = 'Average') -> str:
            """Get statistics for a specific metric"""
            if not self.cloudwatch:
                return "Error: AWS CloudWatch client not available"
            try:
                # Simple implementation - in real world would need date parsing
                # For now just returning a placeholder or error if dates invalid
                return f"Metric stats for {namespace}/{metric_name} (Not fully implemented in this demo)"
            except Exception as e:
                return f"Error getting metrics: {str(e)}"

        @tool
        def describe_alarms() -> str:
            """List current CloudWatch alarms"""
            if not self.cloudwatch:
                return "Error: AWS CloudWatch client not available"
            try:
                response = self.cloudwatch.describe_alarms()
                return str(response.get('MetricAlarms', []))
            except Exception as e:
                return f"Error describing alarms: {str(e)}"
        
        @tool
        def filter_log_events(log_group_name: str, filter_pattern: str = "") -> str:
            """Search logs in a log group"""
            if not self.logs:
                return "Error: AWS Logs client not available"
            try:
                kwargs = {'logGroupName': log_group_name}
                if filter_pattern:
                    kwargs['filterPattern'] = filter_pattern
                
                response = self.logs.filter_log_events(**kwargs)
                return str(response.get('events', []))
            except Exception as e:
                return f"Error filtering logs: {str(e)}"

        # Create the agent
        self.agent = Agent(
            model=model,
            tools=[list_metrics, get_metric_statistics, describe_alarms, filter_log_events],
            system_prompt="""You are an AWS CloudWatch expert. 
            Your job is to help users monitor their infrastructure using CloudWatch metrics and logs.
            Always try to use the available tools to answer questions.
            If you cannot perform an action, explain why."""
        )

        self._initialized = True

    async def run_conversation(self, query: str) -> Dict[str, Any]:
        """Run a conversation with the agent"""
        if not self._initialized:
            await self.initialize()
        
        try:
            response = self.agent(query)
            return {"final_response": response}
        except Exception as e:
            return {"final_response": f"Error running agent: {str(e)}"}

    async def cleanup(self):
        """Cleanup resources"""
        self._initialized = False
        self.agent = None

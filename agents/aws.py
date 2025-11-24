import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from typing import Dict, Any
from core.config import settings

class AWSCloudWatchAgent:
    """
    Agent specialized in AWS CloudWatch operations.
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

        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=settings.AWS_REGION)
            self.logs = boto3.client('logs', region_name=settings.AWS_REGION)
        except Exception as e:
            print(f"Warning: Could not initialize AWS clients: {e}")
        
        model = BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0,
        )

        self.agent = Agent(
            model=model,
            tools=[self.list_metrics, self.get_metric_statistics, self.describe_alarms, self.filter_log_events],
            system_prompt="""You are an AWS CloudWatch expert. 
            Your job is to help users monitor their infrastructure using CloudWatch metrics and logs.
            Always try to use the available tools to answer questions.
            If you cannot perform an action, explain why."""
        )

        self._initialized = True

    @tool
    def list_metrics(self, namespace: str) -> str:
        """List CloudWatch metrics for a given namespace"""
        if not self.cloudwatch:
            return "Error: AWS CloudWatch client not available"
        try:
            response = self.cloudwatch.list_metrics(Namespace=namespace)
            return str(response.get('Metrics', []))
        except Exception as e:
            return f"Error listing metrics: {str(e)}"

    @tool
    def get_metric_statistics(self, namespace: str, metric_name: str, start_time: str, end_time: str, period: int = 300, stat: str = 'Average') -> str:
        """Get statistics for a specific metric"""
        if not self.cloudwatch:
            return "Error: AWS CloudWatch client not available"
        try:
            return f"Metric stats for {namespace}/{metric_name} (Not fully implemented in this demo)"
        except Exception as e:
            return f"Error getting metrics: {str(e)}"

    @tool
    def describe_alarms(self) -> str:
        """List current CloudWatch alarms"""
        if not self.cloudwatch:
            return "Error: AWS CloudWatch client not available"
        try:
            response = self.cloudwatch.describe_alarms()
            return str(response.get('MetricAlarms', []))
        except Exception as e:
            return f"Error describing alarms: {str(e)}"
    
    @tool
    def filter_log_events(self, log_group_name: str, filter_pattern: str = "") -> str:
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

    async def run_conversation(self, query: str) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        
        try:
            response = self.agent(query)
            return {"final_response": response}
        except Exception as e:
            return {"final_response": f"Error running agent: {str(e)}"}

    async def cleanup(self):
        self._initialized = False
        self.agent = None

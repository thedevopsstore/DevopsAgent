import boto3
import threading
import logging
from strands import Agent, tool
from strands.models import BedrockModel
from strands.multiagent.a2a import A2AServer
from core.config import settings

logger = logging.getLogger(__name__)

class AWSCloudWatchAgent:
    """
    Agent specialized in AWS CloudWatch operations.
    Exposed as an A2A server for use by other agents.
    """
    
    def __init__(self):
        self._initialized = False
        self.agent = None
        self.cloudwatch = None
        self.logs = None
        self.a2a_server = None
        self.server_thread = None

    async def initialize(self):
        """Initialize the agent and AWS clients"""
        if self._initialized:
            return

        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=settings.AWS_REGION)
            self.logs = boto3.client('logs', region_name=settings.AWS_REGION)
        except Exception as e:
            logger.warning(f"Could not initialize AWS clients: {e}")
        
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
            If you cannot perform an action, explain why.""",
            name="AWS CloudWatch Agent",
            description="Specialized agent for AWS CloudWatch metrics, logs, and alarms."
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
        # TODO: Implement actual metric statistics retrieval
        return f"Metric stats for {namespace}/{metric_name} (Not fully implemented in this demo)"

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

    async def start_a2a_server(self):
        """Start the A2A server for this agent"""
        if not self._initialized:
            await self.initialize()
        
        if self.a2a_server is not None:
            logger.info("AWS A2A server already running")
            return
        
        try:
            self.a2a_server = A2AServer(
                agent=self.agent,
                host=settings.A2A_HOST,
                port=settings.AWS_A2A_PORT,
                version=settings.A2A_VERSION
            )
            
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True,
                name="aws-a2a-server"
            )
            self.server_thread.start()
            logger.info(f"✅ AWS CloudWatch Agent A2A server started on {settings.A2A_HOST}:{settings.AWS_A2A_PORT}")
        except Exception as e:
            logger.error(f"Failed to start AWS A2A server: {e}", exc_info=True)
            self.a2a_server = None
    
    def _run_server(self):
        """Run the A2A server in a separate thread"""
        try:
            if self.a2a_server:
                self.a2a_server.serve()
        except Exception as e:
            logger.error(f"AWS A2A server error: {e}", exc_info=True)
    
    async def stop_a2a_server(self):
        """Stop the A2A server"""
        if self.a2a_server:
            logger.info("Stopping AWS A2A server...")
            # Note: A2AServer.serve() is blocking, and since it's in a daemon thread,
            # it will exit when the main process exits. We just clear the reference.
            self.a2a_server = None
            self.server_thread = None

    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_a2a_server()
        self._initialized = False
        self.agent = None
        # AWS clients don't need explicit cleanup, but we can clear references
        self.cloudwatch = None
        self.logs = None

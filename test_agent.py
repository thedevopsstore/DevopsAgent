import asyncio
from agents.aws_mcp_agent import AWSCloudWatchAgent

async def main():
    print("Initializing agent...")
    agent = AWSCloudWatchAgent()
    await agent.initialize()
    
    print("Running test query...")
    response = await agent.run_conversation("List metrics for AWS/EC2")
    print(f"Response: {response}")
    
    await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

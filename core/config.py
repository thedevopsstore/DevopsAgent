from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Server Configuration (for UI)
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 9000
    API_VERSION: str = "1.0.0"
    
    # AWS Agent A2A Server Configuration (for agent-to-agent communication)
    A2A_HOST: str = "127.0.0.1"  # Host for A2A servers (AWS agent)
    A2A_VERSION: str = "1.0.0"  # Version for A2A servers
    AWS_A2A_PORT: int = 9001
    
    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_API_MCP_SERVER_URL: Optional[str] = None
    
    # Email Configuration (Optional)
    EMAIL_MCP_SERVER_URL: str = "http://localhost:8100/message"
    EMAIL_POLL_INTERVAL: int = 300
    AUTONOMOUS_SESSION_ID: str = "devops-supervisor-autonomous"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

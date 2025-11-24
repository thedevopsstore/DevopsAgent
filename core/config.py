from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # A2A Server Configuration
    A2A_HOST: str = "127.0.0.1"
    A2A_PORT: int = 9000
    A2A_VERSION: str = "1.0.0"
    
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

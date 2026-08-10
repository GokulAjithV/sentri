from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC: str
    
    # OpenSearch
    OPENSEARCH_ENDPOINT: str
    OPENSEARCH_USERNAME: str
    OPENSEARCH_PASSWORD: str
    
    # LLM
    LLM_PROVIDER: str = "gemini"
    LLM_API_KEY: str
    
    # GitHub
    GITHUB_TOKEN: str
    GITHUB_REPO_URL: str
    
    # Notifications & Routing
    SLACK_WEBHOOK_URL: Optional[str] = None
    DEDUP_WINDOW_MINUTES: int = 15
    MAGIC_LINK_EXPIRY_HOURS: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

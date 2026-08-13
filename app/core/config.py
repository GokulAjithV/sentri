from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC: str
    
    # OpenSearch
    OPENSEARCH_ENDPOINT: Optional[str] = None
    OPENSEARCH_USERNAME: Optional[str] = None
    OPENSEARCH_PASSWORD: Optional[str] = None
    OPENSEARCH_INDEX_PATTERN: str = "logstash-*"
    
    # LLM
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL_NAME: str = "gemini-2.5-flash"
    LLM_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # GitHub
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPO_URLS: Optional[str] = None # Comma-separated list of repos, e.g., https://github.com/org/repo1,https://github.com/org/repo2
    
    # Notifications & Routing
    SLACK_WEBHOOK_URL: Optional[str] = None
    
    # SMTP Email Notifier (Optional fallback)
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    ALERT_TO_EMAIL: Optional[str] = None
    
    DEDUP_WINDOW_MINUTES: int = 15
    MAGIC_LINK_EXPIRY_HOURS: int = 1
    JWT_SECRET: str
    CHAT_UI_BASE_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

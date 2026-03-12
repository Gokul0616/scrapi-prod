from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Scrapi API'
    database_url: str = 'postgresql+psycopg2://scrapi:scrapi@localhost:5432/scrapi'
    redis_url: str = 'redis://localhost:6379/0'
    api_key: str = 'dev-secret-key'
    webhook_timeout_sec: int = 10
    queue_lease_seconds: int = 120
    queue_max_attempts: int = 3
    queue_retry_backoff_seconds: int = 30


settings = Settings()

from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    service_name: str = "decision-service"
    port: int = 8301
    log_level: str = "DEBUG"
    database_url: str = "postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform"
    aws_endpoint_url: str = "http://localstack:4566"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_default_region: str = "us-east-1"
    consume_queue: str = "decision-queue"
    model_config = {"env_prefix": "", "extra": "ignore"}


settings = ServiceSettings()

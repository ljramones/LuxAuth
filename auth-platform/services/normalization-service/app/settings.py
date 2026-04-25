import sys

sys.path.insert(0, "/app/libs/auth_common")

from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    service_name: str = "normalization-service"
    port: int = 8202
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform"
    aws_endpoint_url: str | None = None
    s3_raw_bucket: str = "auth-platform-raw-evidence"
    s3_normalized_bucket: str = "auth-platform-normalized-evidence"
    sqs_normalization_queue: str = "normalization-queue"
    sqs_embedding_queue: str = "embedding-queue"
    consume_queue: str = "normalization-queue"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = ServiceSettings()

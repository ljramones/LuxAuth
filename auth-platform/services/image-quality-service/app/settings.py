import sys

sys.path.insert(0, "/app/libs/auth_common")

from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    service_name: str = "image-quality-service"
    port: int = 8201
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform"
    aws_endpoint_url: str | None = None
    s3_raw_bucket: str = "auth-platform-raw-evidence"
    sqs_quality_queue: str = "image-quality-queue"
    sqs_normalization_queue: str = "normalization-queue"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = ServiceSettings()

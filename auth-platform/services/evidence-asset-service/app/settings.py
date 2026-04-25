from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    service_name: str = "evidence-asset-service"
    port: int = 8104
    log_level: str = "DEBUG"
    database_url: str = "postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform"
    aws_endpoint_url: str = "http://localstack:4566"
    raw_evidence_bucket: str = "auth-platform-raw-evidence"
    image_upload_queue: str = "image-quality-queue"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = ServiceSettings()

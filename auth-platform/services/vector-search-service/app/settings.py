import sys

sys.path.insert(0, "/app/libs/auth_common")

from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    service_name: str = "vector-search-service"
    port: int = 8204
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform"
    aws_endpoint_url: str | None = None
    sqs_vector_search_queue: str = "vector-search-queue"
    sqs_region_scoring_queue: str = "region-scoring-queue"
    top_k: int = 5
    consume_queue: str = "vector-search-queue"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = ServiceSettings()

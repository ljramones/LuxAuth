"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


# S3 bucket name constants
S3_BUCKET_RAW_EVIDENCE = "auth-platform-raw-evidence"
S3_BUCKET_NORMALIZED_EVIDENCE = "auth-platform-normalized-evidence"
S3_BUCKET_REFERENCE_LIBRARY = "auth-platform-reference-library"
S3_BUCKET_ML_ARTIFACTS = "auth-platform-ml-artifacts"

# SQS queue name constants
SQS_IMAGE_QUALITY_QUEUE = "image-quality-queue"
SQS_NORMALIZATION_QUEUE = "normalization-queue"
SQS_EMBEDDING_QUEUE = "embedding-queue"
SQS_VECTOR_SEARCH_QUEUE = "vector-search-queue"
SQS_REGION_SCORING_QUEUE = "region-scoring-queue"
SQS_DECISION_QUEUE = "decision-queue"
SQS_DEAD_LETTER_QUEUE = "dead-letter-queue"


class Settings(BaseSettings):
    """Shared configuration for all platform services."""

    service_name: str = "auth-service"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform"

    aws_endpoint_url: str = "http://localstack:4566"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_default_region: str = "us-east-1"

    correlation_header: str = "X-Correlation-ID"

    model_config = {
        "env_prefix": "",
        "extra": "ignore",
    }

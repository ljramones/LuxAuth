from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    service_name: str = "scan-session-service"
    port: int = 8101
    log_level: str = "DEBUG"
    database_url: str = "postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform"
    aws_endpoint_url: str = "http://localstack:4566"
    scan_recipe_service_url: str = "http://scan-recipe-service:8102"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = ServiceSettings()

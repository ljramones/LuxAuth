from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    service_name: str = "ml-diagnostics-service"
    port: int = 8401
    log_level: str = "DEBUG"
    database_url: str = "postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform"
    reports_dir: str = "/app/reports/ml-diagnostics"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = ServiceSettings()

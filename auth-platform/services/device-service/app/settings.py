from pydantic_settings import BaseSettings


class ServiceSettings(BaseSettings):
    service_name: str = "device-service"
    port: int = 8103
    log_level: str = "DEBUG"
    database_url: str = "postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform"

    model_config = {"env_prefix": "", "extra": "ignore"}


settings = ServiceSettings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    stock_list_name: str = "ストック"
    flow_list_name: str = "フロー"
    timezone: str = "Asia/Tokyo"
    port: int = 8080
    api_token: str = ""
    log_level: str = "INFO"


settings = Settings()

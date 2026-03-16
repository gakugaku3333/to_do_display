from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    icloud_apple_id: str = ""
    icloud_app_password: str = ""
    stock_list_name: str = "ストック"
    flow_list_name: str = "フロー"
    timezone: str = "Asia/Tokyo"
    port: int = 8080


settings = Settings()

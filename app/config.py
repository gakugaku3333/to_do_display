from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    stock_list_name: str = "ストック"
    flow_list_name: str = "フロー"
    timezone: str = "Asia/Tokyo"
    port: int = 8080
    api_token: str = ""
    log_level: str = "INFO"

    # 学校配布物機能
    gemini_api_key: str = ""
    children: str = "紗奈,和花,舞"  # カンマ区切りで子供の名前

    @property
    def children_list(self) -> list[str]:
        return [c.strip() for c in self.children.split(",") if c.strip()]


settings = Settings()

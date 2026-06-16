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

    # Google Calendar
    # 夫アカウントの calendarList に出ない共有ファミリーカレンダーを明示追加する
    family_calendar_id: str = ""
    # 取得対象から除外するカレンダーID（カンマ区切り）。
    # 例: freeBusyReader 権限しか無い大学アカウントなど（403 でログが汚れる）
    excluded_calendar_ids: str = ""

    @property
    def children_list(self) -> list[str]:
        return [c.strip() for c in self.children.split(",") if c.strip()]

    @property
    def excluded_calendar_ids_set(self) -> set[str]:
        return {c.strip() for c in self.excluded_calendar_ids.split(",") if c.strip()}


settings = Settings()

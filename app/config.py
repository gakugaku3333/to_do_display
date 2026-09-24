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

    # Google Home 音声ブリーフィング（Cast で再生）
    # Google Home アプリに表示されるスピーカー名。空欄なら機能無効
    google_home_name: str = ""
    # 毎朝の自動再生時刻 "HH:MM"。空欄なら自動再生しない
    briefing_cast_time: str = ""
    # macOS `say` の音声名（日本語: Kyoko / Otoya など）
    tts_voice: str = "Kyoko"
    # 再生時の音量 0.0〜1.0。負値なら変更しない
    google_home_volume: float = -1.0
    # Google Home から見た本サーバーのURL。空欄なら LAN IP を自動検出
    public_base_url: str = ""

    @property
    def children_list(self) -> list[str]:
        return [c.strip() for c in self.children.split(",") if c.strip()]

    @property
    def excluded_calendar_ids_set(self) -> set[str]:
        return {c.strip() for c in self.excluded_calendar_ids.split(",") if c.strip()}


settings = Settings()

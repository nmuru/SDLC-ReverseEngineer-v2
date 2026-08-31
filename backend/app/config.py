from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_provider: str = "openrouter"
    openai_model: str = "openrouter/free"
    openrouter_api_key: str | None = None
    allowed_origins: str = "http://localhost:3000"
    phases_per_batch: int = 1
    batch_mode: str = "parallel"
    analysis_results_dir: str = "output-content"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def agent_model(self) -> str:
        return self.openai_model


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_provider: str = "anthropic"
    anthropic_model: str = "claude-sonnet-5"
    anthropic_api_key: str | None = None
    allowed_origins: str = "http://localhost:3000"
    # allowed_origins: str = "https://sdlc-reverse-engineer.vercel.app"
    phases_per_batch: int = 1
    batch_mode: str = "parallel"
    analysis_results_dir: str = "output-content"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def agent_model(self) -> str:
        return self.anthropic_model


settings = Settings()

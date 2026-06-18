from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LOG_LEVEL: str = "DEBUG"
    ENV: str = "local"
    APP_NAME: str = "C Rag API"
    APP_VERSION: str = "0.1.0"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5444
    DB_NAME: str = "c_rag"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_ECHO: bool = False

    EMBEDDING_DIM: int = 768  # Change to match your model (768 gemini, 1536 openai-small, 3072 openai-large)

    CORS_ALLOWED_URL: str | None = None

    # Internal service-to-service auth
    INTERNAL_TOKEN: str | None = None

    def validate_env_variables(self) -> None:
        required = {
            "CORS_ALLOWED_URL": self.CORS_ALLOWED_URL,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
if settings.ENV not in ("test", "unittest"):
    settings.validate_env_variables()

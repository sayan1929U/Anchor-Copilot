from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60
    groq_api_key_1: str | None = None
    groq_api_key_2: str | None = None
    groq_api_key_3: str | None = None
    allowed_origin: str = "http://127.0.0.1:8000"

    class Config:
        env_file = ".env"

settings = Settings()

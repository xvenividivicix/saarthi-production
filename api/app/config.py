from pydantic_settings import BaseSettings
from pydantic import Field  # ✅ just one import line, clean

class Settings(BaseSettings):
    app_env: str = Field(default="dev")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    api_prefix: str = Field(default="/v1")

    cors_allowed_origins: str = Field(default="http://localhost:5173,http://localhost:3000")

    jwt_alg: str = Field(default="RS256")
    jwt_private_key_path: str = Field(default="/run/secrets/jwt_private.pem")
    jwt_public_key_path: str = Field(default="/run/secrets/jwt_public.pem")
    access_token_expires_min: int = Field(default=60)

    db_url: str = Field(default="sqlite:///./data/app.db")
    redis_url: str = Field(default="redis://localhost:6379/0")

    es_url: str = Field(default="http://localhost:9200")
    es_index_icd: str = Field(default="icd_tm")

    icd_api_base: str = Field(default="https://id.who.int/icd/release/11")
    icd_api_token: str | None = None
    icd_release_id: str = Field(default="2025-01")
    icd_linearization: str = Field(default="mms")  # ✅ ADD THIS LINE


    rate_limit_rps: int = Field(default=20)

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://kaninchen:kaninchen_dev@localhost:5432/kaninchenzucht"
    cors_origins: str = "http://localhost:5173"
    storage_dir: str = "./storage"
    anthropic_api_key: str = ""
    secure_cookies: bool = False  # in Produktion (echtes HTTPS) auf True setzen

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        # Hoster (z.B. Railway) geben DATABASE_URL oft als postgres://... oder
        # postgresql://... ohne den psycopg3-Treiber-Suffix aus.
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

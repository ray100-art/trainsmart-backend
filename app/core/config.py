from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "TrainSMART"
    APP_VERSION: str = "2.0"
    ENVIRONMENT: str = "development"  # "development" | "production"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str  # No default — MUST be in .env
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 1800  # 30 min — recycle connections before PostgreSQL's idle timeout

    # ── JWT ───────────────────────────────────────────────────────────────────
    SECRET_KEY: str    # No default — MUST be in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    COOKIE_NAME: str = "trainsmart_token"
    COOKIE_SECURE: bool = False   # set True in production (HTTPS)
    COOKIE_SAMESITE: str = "lax"

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── Frontend ──────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    # ── Rate limiting ─────────────────────────────────────────────────────────
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # ── Email (Gmail SMTP) ────────────────────────────────────────────────────
    EMAIL_FROM: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_ENABLED: bool = True

    # ── Rate limit (verify endpoint) ──────────────────────────────────────────
    VERIFY_RATE_LIMIT_MAX: int = 30
    VERIFY_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── Rate limit storage ────────────────────────────────────────────────────
    # "memory"   — in-process dict; fast, works for single-worker deployments
    # "database" — PostgreSQL-backed; survives restarts, works across workers
    RATE_LIMIT_STORAGE: str = "memory"

    # Trust X-Forwarded-For / X-Real-IP only behind a reverse proxy (nginx).
    TRUST_PROXY_HEADERS: bool = False

    # Comma-separated hostnames; empty = disabled. Example: nhcsc.nascop.org,api.example.com
    TRUSTED_HOSTS: str = ""

    # Hard cap for M&E CSV exports (rows). Prevents OOM on national dumps.
    EXPORT_MAX_ROWS: int = 10000

    # Optional Moodle LMS base URL (legacy Moodle menu)
    MOODLE_URL: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if v == "change-this-to-a-long-random-string-in-production":
            raise ValueError(
                "SECRET_KEY is still the default placeholder. "
                "Generate a real key with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_not_be_sqlite_in_production(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and v.startswith("sqlite"):
            raise ValueError("SQLite cannot be used in production. Use PostgreSQL.")
        return v

    @field_validator("COOKIE_SAMESITE")
    @classmethod
    def cookie_samesite_valid(cls, v: str) -> str:
        allowed = {"strict", "lax", "none"}
        if v.lower() not in allowed:
            raise ValueError(f"COOKIE_SAMESITE must be one of: {', '.join(sorted(allowed))}.")
        return v.lower()

    @property
    def cookie_secure(self) -> bool:
        return self.COOKIE_SECURE or self.is_production

    @property
    def cookie_samesite_effective(self) -> str:
        # Cross-origin hosting (e.g. Vercel FE + Render API) requires SameSite=None
        # with Secure. Same-origin MoH deploy should use lax (default).
        return self.COOKIE_SAMESITE

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def trusted_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.TRUSTED_HOSTS.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def rate_limit_use_database(self) -> bool:
        # Multi-worker production always needs shared storage
        if self.is_production:
            return True
        return self.RATE_LIMIT_STORAGE == "database"

    @property
    def docs_enabled(self) -> bool:
        return not self.is_production

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

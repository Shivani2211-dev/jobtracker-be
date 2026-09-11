from pydantic_settings import BaseSettings, SettingsConfigDict

# The fallback signing key. Fine for local development; production refuses it.
INSECURE_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    app_name: str = "AI Job Tracker"
    environment: str = "development"
    database_url: str = "sqlite:///./jobtracker.db"
    secret_key: str = INSECURE_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    # One origin, or several separated by commas.
    frontend_origin: str = "http://localhost:3000"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    demo_email: str = "demo@example.com"
    demo_password: str | None = None
    max_resume_bytes: int = 1_000_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def sqlalchemy_url(self) -> str:
        """Hosts such as Render hand out postgres:// URLs. SQLAlchemy needs the
        driver named, and this project installs psycopg 3, not psycopg2."""
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def allowed_origins(self) -> list[str]:
        origins = [o.strip().rstrip("/") for o in self.frontend_origin.split(",") if o.strip()]
        if not self.is_production:
            origins += [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3001",
            ]
        return list(dict.fromkeys(origins))

    def check_production_safety(self) -> None:
        """Fail at startup rather than run insecurely. With the default key in a
        public repo, anyone could sign a login token for any user."""
        if not self.is_production:
            return
        if self.secret_key == INSECURE_SECRET or len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must be a random value of at least 32 characters in production.")
        if self.sqlalchemy_url.startswith("sqlite"):
            raise RuntimeError("Production needs a persistent database: set DATABASE_URL to Postgres.")


settings = Settings()

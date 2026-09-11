import pytest

from app.core.config import INSECURE_SECRET, Settings


def make(**overrides):
    return Settings(_env_file=None, **overrides)


def test_postgres_urls_get_the_psycopg_driver():
    assert make(database_url="postgres://u:p@host:5432/db").sqlalchemy_url == "postgresql+psycopg://u:p@host:5432/db"
    assert make(database_url="postgresql://u:p@host/db").sqlalchemy_url == "postgresql+psycopg://u:p@host/db"
    assert make(database_url="sqlite:///./x.db").sqlalchemy_url == "sqlite:///./x.db"


def test_production_refuses_the_default_secret():
    settings = make(environment="production", secret_key=INSECURE_SECRET, database_url="postgres://u:p@h/db")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        settings.check_production_safety()


def test_production_refuses_sqlite():
    settings = make(environment="production", secret_key="x" * 40, database_url="sqlite:///./x.db")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        settings.check_production_safety()


def test_production_starts_with_real_values():
    make(environment="production", secret_key="x" * 40, database_url="postgres://u:p@h/db").check_production_safety()


def test_cors_origins_are_split_and_localhost_is_dev_only():
    prod = make(environment="production", frontend_origin="https://a.vercel.app, https://b.example.com/")
    assert prod.allowed_origins == ["https://a.vercel.app", "https://b.example.com"]
    dev = make(environment="development", frontend_origin="http://localhost:3000")
    assert "http://localhost:3001" in dev.allowed_origins

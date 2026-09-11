"""Shared test setup: a throwaway SQLite database whose schema comes from the models."""

import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parent.parent / "test_jobtracker.db"
# Set before anything imports app.core.config.
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["ENVIRONMENT"] = "development"
os.environ["OPENAI_API_KEY"] = ""  # always exercise the deterministic fallback
os.environ["DEMO_PASSWORD"] = ""

import uuid  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import models  # noqa: E402,F401


@pytest.fixture(scope="session", autouse=True)
def schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def make_user(client):
    """Register a fresh user; returns (email, auth headers)."""

    def _make(email: str | None = None, password: str = "secret123"):
        email = email or f"user-{uuid.uuid4().hex[:10]}@example.com"
        response = client.post(
            "/auth/register", json={"email": email, "full_name": "Test User", "password": password}
        )
        assert response.status_code == 200, response.text
        return email, {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _make

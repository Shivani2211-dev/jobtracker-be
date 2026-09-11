from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_register_create_job_and_analyze():
    register = client.post(
        "/auth/register",
        json={"email": "test@example.com", "full_name": "Test User", "password": "secret123"},
    )
    assert register.status_code in (200, 400)

    login = client.post("/auth/login", json={"email": "test@example.com", "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resume = client.put(
        "/auth/resume",
        json={"resume_text": "Python FastAPI SQLAlchemy React analytics dashboard"},
        headers=headers,
    )
    assert resume.status_code == 200

    job = client.post(
        "/jobs",
        json={
            "company": "Acme",
            "title": "Full Stack Engineer",
            "description": "Build Python FastAPI services and React dashboards with PostgreSQL.",
        },
        headers=headers,
    )
    assert job.status_code == 200
    job_id = job.json()["id"]

    analysis = client.post(f"/analyze/job/{job_id}", headers=headers)
    assert analysis.status_code == 200
    assert 0 <= analysis.json()["fit_score"] <= 100

    application = client.post(
        "/applications",
        json={"company": "Acme", "title": "Full Stack Engineer", "status": "Applied", "job_id": job_id},
        headers=headers,
    )
    assert application.status_code == 200

    analytics = client.get("/applications/analytics/summary", headers=headers)
    assert analytics.status_code == 200
    assert analytics.json()["total_applications"] >= 1

    cover_letter = client.post(
        "/analyze/cover-letter",
        json={"company": "Acme", "title": "Full Stack Engineer", "job_description": "Python FastAPI React"},
        headers=headers,
    )
    assert cover_letter.status_code == 200
    assert "cover_letter" in cover_letter.json()

    questions = client.post(
        "/analyze/interview-questions",
        json={"job_description": "Python FastAPI React"},
        headers=headers,
    )
    assert questions.status_code == 200
    assert questions.json()["questions"]

"""Regression tests for the bugs fixed before the first deploy."""

import uuid

from app.core.security import create_access_token


def _job(client, headers, **overrides):
    body = {"company": "Contoso", "title": "Engineer", "description": "Python FastAPI React"} | overrides
    response = client.post("/jobs", json=body, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_users_cannot_reach_each_others_jobs(client, make_user):
    _, alice = make_user()
    _, bob = make_user()
    job_id = _job(client, alice)

    assert all(job["id"] != job_id for job in client.get("/jobs", headers=bob).json())
    assert client.patch(f"/jobs/{job_id}", json={"title": "Hijacked"}, headers=bob).status_code == 404
    assert client.delete(f"/jobs/{job_id}", headers=bob).status_code == 404
    assert client.post(f"/analyze/job/{job_id}", headers=bob).status_code == 404


def test_applications_cannot_point_at_another_users_job(client, make_user):
    _, alice = make_user()
    _, bob = make_user()
    alice_job = _job(client, alice)

    created = client.post("/applications", json={"company": "C", "title": "E", "job_id": alice_job}, headers=bob)
    assert created.status_code == 404

    own = client.post("/applications", json={"company": "C", "title": "E"}, headers=bob)
    assert own.status_code == 200
    relinked = client.patch(f"/applications/{own.json()['id']}", json={"job_id": alice_job}, headers=bob)
    assert relinked.status_code == 404


def test_resume_parse_requires_login(client):
    response = client.post("/resume/parse", files={"file": ("cv.txt", b"Python developer", "text/plain")})
    assert response.status_code == 401


def test_resume_upload_rejects_oversized_and_binary_files(client, make_user):
    _, headers = make_user()
    too_big = b"a" * (1_000_000 + 1)
    response = client.post("/resume/upload", files={"file": ("cv.txt", too_big, "text/plain")}, headers=headers)
    assert response.status_code == 413

    pdf = b"%PDF-1.7" + bytes([0, 1]) + b" not text"
    response = client.post("/resume/upload", files={"file": ("cv.pdf", pdf, "application/pdf")}, headers=headers)
    assert response.status_code == 415

    ok = client.post("/resume/upload", files={"file": ("cv.txt", b"Python FastAPI React", "text/plain")}, headers=headers)
    assert ok.status_code == 200
    assert "python" in ok.json()["resume_skills"]


def test_follow_up_dates_save_and_analytics_counts_them(client, make_user):
    _, headers = make_user()
    for when in ("2020-01-01T09:00:00", "2020-01-01T09:00:00+05:30", "2999-01-01T09:00:00Z"):
        response = client.post(
            "/applications", json={"company": "Contoso", "title": "Engineer", "follow_up_date": when}, headers=headers
        )
        assert response.status_code == 200, response.text

    summary = client.get("/applications/analytics/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["follow_ups_due"] == 2


def test_times_are_stored_and_returned_in_utc(client, make_user):
    _, headers = make_user()
    response = client.post(
        "/applications",
        json={"company": "Contoso", "title": "Engineer", "follow_up_date": "2026-09-20T14:30:00-04:00"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["follow_up_date"].startswith("2026-09-20T18:30:00")
    assert body["follow_up_date"].endswith(("Z", "+00:00"))
    assert body["created_at"].endswith(("Z", "+00:00"))


def test_login_ignores_email_case_and_blocks_case_duplicates(client, make_user):
    email = f"Mixed-{uuid.uuid4().hex[:8]}@Example.com"
    make_user(email=email)
    assert client.post("/auth/login", json={"email": email.lower(), "password": "secret123"}).status_code == 200
    duplicate = client.post("/auth/register", json={"email": email.upper(), "full_name": "X", "password": "secret123"})
    assert duplicate.status_code == 400


def test_overlong_fields_are_rejected_instead_of_crashing(client, make_user):
    _, headers = make_user()
    response = client.post("/jobs", json={"company": "C" * 300, "title": "T", "description": "D"}, headers=headers)
    assert response.status_code == 422


def test_token_with_non_numeric_subject_gets_401(client):
    token = create_access_token("not-a-number")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_auth_resume_update_refreshes_parsed_skills(client, make_user):
    _, headers = make_user()
    client.put("/auth/resume", json={"resume_text": "Python FastAPI"}, headers=headers)
    updated = client.put("/auth/resume", json={"resume_text": "React TypeScript"}, headers=headers).json()
    assert "react" in updated["resume_skills"]
    assert "python" not in updated["resume_skills"]


def test_cover_letter_is_signed_with_the_users_name(client, make_user):
    _, headers = make_user()
    response = client.post(
        "/analyze/cover-letter",
        json={"company": "Contoso", "title": "Engineer", "job_description": "Python"},
        headers=headers,
    )
    assert response.json()["cover_letter"].rstrip().endswith("Test User")

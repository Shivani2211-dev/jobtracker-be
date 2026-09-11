RESUME = "Built dashboards in React and TypeScript for finance teams.\nWrote FastAPI services backed by PostgreSQL."


def test_tailor_requires_login(client):
    assert client.post("/analyze/tailor", json={"job_description": "React engineer"}).status_code == 401


def test_tailor_needs_a_resume(client, make_user):
    _, headers = make_user()
    response = client.post("/analyze/tailor", json={"job_description": "React engineer"}, headers=headers)
    assert response.status_code == 400


def test_tailor_uses_the_saved_resume_and_never_claims_gaps(client, make_user):
    _, headers = make_user()
    assert client.put("/resume", json={"resume_text": RESUME}, headers=headers).status_code == 200

    response = client.post(
        "/analyze/tailor", json={"job_description": "React engineer; Kubernetes a plus"}, headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "extractive"
    assert body["bullets"]
    assert all(bullet["evidence"] in RESUME.splitlines() for bullet in body["bullets"])
    assert "kubernetes" in body["missing_keywords"]
    assert not any("kubernetes" in bullet["text"].lower() for bullet in body["bullets"])


def test_tailor_accepts_pasted_resume_text(client, make_user):
    _, headers = make_user()
    response = client.post(
        "/analyze/tailor",
        json={"job_description": "FastAPI and PostgreSQL backend role", "resume_text": RESUME},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["bullets"][0]["evidence"] == "Wrote FastAPI services backed by PostgreSQL."

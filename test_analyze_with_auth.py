from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Create a user
register_response = client.post(
    "/auth/register",
    json={"email": "test@test.com", "full_name": "Test User", "password": "test123"}
)
print(f"Register Status: {register_response.status_code}")
print(f"Register Response: {register_response.json()}")

if register_response.status_code == 200:
    data = register_response.json()
    token = data.get("access_token")
    user_id = data.get("user", {}).get("id")
    print(f"\nUser ID: {user_id}")
    print(f"Token: {token}")
    
    # Now test the analyze endpoint
    headers = {"Authorization": f"Bearer {token}"}
    analyze_response = client.post(
        "/analyze",
        json={"job_description": "Front-end Architect role requiring React", "resume_text": "SHIVANI - React.js, FastAPI"},
        headers=headers
    )
    print(f"\nAnalyze Status: {analyze_response.status_code}")
    print(f"Analyze Response: {analyze_response.json()}")

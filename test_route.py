from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# First, let's test if authentication is working
response = client.post(
    "/auth/login",
    json={"email": "test@test.com", "password": "test123"}
)
print(f"Login Response: {response.status_code}")
print(f"Login Content: {response.text}")

# Now test the analyze endpoint
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwiZXhwIjoxNzg2NjIxODQ0fQ.FOAf-V58nqB4JBY1AliZrkRld0a3P4nMrxGPWPKgTLw"
}

response = client.post(
    "/analyze",
    json={"job_description": "Test job", "resume_text": "Test resume"},
    headers=headers
)
print(f"\nAnalyze Response: {response.status_code}")
print(f"Analyze Content: {response.text}")
print(f"Analyze JSON: {response.json() if response.status_code == 200 else 'N/A'}")

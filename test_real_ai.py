from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Create a user
register_response = client.post(
    "/auth/register",
    json={"email": "aitest@test.com", "full_name": "AI Test User", "password": "test123"}
)
token = register_response.json()["access_token"]

# Update resume first
resume_text = """
SHIVANI REDDY ROKKAM
Senior Full-Stack Developer | React.js, FastAPI, PostgreSQL

PROFESSIONAL SUMMARY
Experienced full-stack developer with 4+ years building scalable web applications. Expert in modern React architectures, backend API design, and cloud deployment.

TECHNICAL SKILLS
Frontend: React.js, TypeScript, Next.js, Tailwind CSS, Redux
Backend: Python (FastAPI, Django), Node.js, PostgreSQL, MongoDB
DevOps: AWS (EC2, S3, Lambda), Docker, Kubernetes, GitHub Actions

WORK EXPERIENCE
Senior Frontend Developer – TechCorp Inc. (Jan 2023 - Present)
- Led design and implementation of component library reducing development time by 40%
- Architected micro-frontend solution supporting 3+ independent teams
- Implemented advanced performance optimizations (lazy loading, code splitting)

Full-Stack Developer – StartupXYZ (Jun 2021 - Dec 2022)
- Built production FastAPI backend serving 10k+ daily users
- Developed React dashboard with real-time updates using WebSockets
- Managed PostgreSQL database with complex queries and optimization

PROJECTS
ExpenseFlow - Cloud SaaS Expense Management
- Architected full-stack application with React frontend and FastAPI backend
- Implemented JWT auth, role-based access, Redis caching
- Deployed to AWS with automated CI/CD pipelines
"""

client.put("/auth/resume", json={"resume_text": resume_text}, headers={"Authorization": f"Bearer {token}"})

# Test with detailed job description
job_desc = """
FRONT-END ARCHITECT ROLE

We are seeking an experienced Front-End Architect to lead our web platform development.

RESPONSIBILITIES:
- Design and architect scalable React/Next.js applications
- Lead frontend technical decisions and code review process
- Implement performance optimization strategies
- Mentor junior developers on best practices
- Work with design and backend teams on seamless integration

REQUIREMENTS:
- 5+ years of frontend development experience
- Expert knowledge of React.js and TypeScript
- Strong understanding of web performance optimization
- Experience with micro-frontends and component libraries
- Proficiency with Git and modern CI/CD practices
- Experience with AWS or similar cloud platforms

NICE TO HAVE:
- Next.js experience
- Kubernetes knowledge
- GraphQL experience
"""

print("Testing real AI analysis...")
analyze_response = client.post(
    "/analyze",
    json={"job_description": job_desc, "resume_text": resume_text},
    headers={"Authorization": f"Bearer {token}"}
)

result = analyze_response.json()
print(f"\nFit Score: {result['fit_score']}")
print(f"Summary: {result['summary']}")
print(f"\nStrengths:")
for s in result['strengths']:
    print(f"  - {s}")
print(f"\nGaps:")
for g in result['gaps']:
    print(f"  - {g}")
print(f"\nSuggested Edits:")
for e in result['suggested_edits']:
    print(f"  - {e}")

"""Create or reset the public demo account.

Runs on every deploy start. It does nothing unless DEMO_PASSWORD is set, and
when it runs it wipes and recreates the demo user's data, so whatever visitors
did to the shared account is undone on the next restart.

Usage (from the backend directory):  python -m scripts.seed_demo
"""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.models import Application, Job, User
from app.services.ai_service import _fallback_analysis

DEMO_RESUME = """Alex Rivera - Full Stack Developer

Builds web applications with React, TypeScript and Next.js on the frontend and
Python, FastAPI and PostgreSQL on the backend. Comfortable with Docker, REST API
design, SQL data modelling and writing automated tests. Has shipped analytics
dashboards and internal tools for small product teams."""

# Fictional companies only - this account is public.
DEMO_JOBS = [
    ("Northwind Labs", "Full Stack Engineer", "Interview", "Remote",
     "Build React and TypeScript features backed by Python FastAPI services and PostgreSQL. "
     "Own features end to end, write tests, and deploy with Docker."),
    ("Contoso Health", "Backend Developer", "Applied", "Boston, MA",
     "Design REST APIs in Python, model data in PostgreSQL, and keep services reliable. "
     "Experience with Docker and CI pipelines is a plus."),
    ("Fabrikam Analytics", "Frontend Engineer", "Applied", "New York, NY",
     "Create data-heavy dashboards in React and TypeScript. Care about accessibility, "
     "performance and a clean component library."),
    ("Globex Cloud", "Platform Engineer", "Rejected", "Seattle, WA",
     "Run Kubernetes clusters on AWS, manage Terraform infrastructure, and improve "
     "observability with Prometheus and Grafana."),
    ("Acme Robotics", "Software Engineer, Tools", "Offer", "Pittsburgh, PA",
     "Build internal web tools with Next.js and FastAPI. Work closely with operators "
     "to turn manual workflows into software."),
]


def run() -> None:
    if not settings.demo_password:
        print("seed_demo: DEMO_PASSWORD not set, skipping")
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == settings.demo_email).first()
        if user is None:
            user = User(email=settings.demo_email, full_name="Alex Rivera", hashed_password="")
            db.add(user)

        user.full_name = "Alex Rivera"
        user.hashed_password = hash_password(settings.demo_password)
        user.resume_text = DEMO_RESUME
        user.resume_filename = "alex-rivera-resume.txt"
        user.resume_summary = " ".join(DEMO_RESUME.split()[:35])
        user.resume_skills = "python, fastapi, react, typescript, postgresql, docker, sql, api"

        # Reset whatever visitors changed on the shared account.
        db.query(Application).filter(Application.user_id == user.id).delete()
        db.query(Job).filter(Job.user_id == user.id).delete()
        db.flush()

        now = datetime.now(timezone.utc)
        for index, (company, title, status, location, description) in enumerate(DEMO_JOBS):
            analysis = _fallback_analysis(description, DEMO_RESUME)
            job = Job(
                user_id=user.id,
                company=company,
                title=title,
                status=status,
                location=location,
                description=description,
                fit_score=analysis.fit_score,
                ai_feedback=analysis.summary,
            )
            db.add(job)
            db.flush()
            db.add(
                Application(
                    user_id=user.id,
                    job_id=job.id,
                    company=company,
                    title=title,
                    status=status,
                    source="Company website" if index % 2 else "Referral",
                    follow_up_date=now + timedelta(days=index * 3 - 4),
                    reminder_note="Send a short follow-up email" if status == "Applied" else None,
                )
            )

        db.commit()
        print(f"seed_demo: demo account {settings.demo_email} is ready")
    finally:
        db.close()


if __name__ == "__main__":
    run()

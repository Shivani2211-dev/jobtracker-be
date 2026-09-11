from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analyze, applications, auth, jobs, resume
from app.core.config import settings

# Refuse to start in production with a guessable signing key or a throwaway
# SQLite file. Tables come from Alembic migrations (`alembic upgrade head`), not
# from create_all() at import time - that shortcut is how the local database
# drifted away from the migration history.
settings.check_production_safety()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    # Auth travels in the Authorization header, not in cookies.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(resume.router)
app.include_router(analyze.router)


@app.get("/health")
def health():
    return {"status": "ok"}

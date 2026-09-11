from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


def _utc(value: datetime | None) -> datetime | None:
    """Keep every instant in UTC. A value with no zone is treated as UTC:
    SQLite drops the zone when it reads a value back, and Postgres would read a
    bare value in its own session timezone and shift it."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# Max lengths mirror the String(n) columns. SQLite ignores them; Postgres
# rejects an over-long value with an error that surfaced as a 500.
NAME = 255
URL = 500


class JobStatus(str, Enum):
    applied = "Applied"
    interview = "Interview"
    offer = "Offer"
    rejected = "Rejected"


class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=NAME)
    full_name: str = Field(min_length=1, max_length=NAME)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.strip().lower()


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    resume_text: str | None = None
    resume_filename: str | None = None
    resume_summary: str | None = None
    resume_skills: str | None = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.strip().lower()


class ResumeUpdate(BaseModel):
    resume_text: str
    resume_filename: str | None = Field(default=None, max_length=NAME)


class ResumeParseResult(BaseModel):
    resume_text: str
    summary: str
    skills: list[str]


class JobCreate(BaseModel):
    company: str = Field(max_length=NAME)
    title: str = Field(max_length=NAME)
    description: str
    status: JobStatus = JobStatus.applied
    location: str | None = Field(default=None, max_length=NAME)
    url: str | None = Field(default=None, max_length=URL)
    notes: str | None = None


class JobUpdate(BaseModel):
    company: str | None = Field(default=None, max_length=NAME)
    title: str | None = Field(default=None, max_length=NAME)
    description: str | None = None
    status: JobStatus | None = None
    location: str | None = Field(default=None, max_length=NAME)
    url: str | None = Field(default=None, max_length=URL)
    notes: str | None = None


class JobOut(JobCreate):
    id: int
    fit_score: int | None = None
    ai_feedback: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("created_at", "updated_at")
    @classmethod
    def _timestamps_utc(cls, value: datetime) -> datetime:
        return _utc(value)


class AnalyzeRequest(BaseModel):
    job_description: str
    resume_text: str | None = None


class AIAnalysisResult(BaseModel):
    fit_score: int
    strengths: list[str]
    gaps: list[str]
    suggested_edits: list[str]
    summary: str


class CoverLetterRequest(BaseModel):
    job_description: str
    company: str
    title: str
    resume_text: str | None = None


class CoverLetterResult(BaseModel):
    cover_letter: str


class InterviewQuestionResult(BaseModel):
    questions: list[str]


class ApplicationCreate(BaseModel):
    company: str = Field(max_length=NAME)
    title: str = Field(max_length=NAME)
    status: JobStatus = JobStatus.applied
    job_id: int | None = None
    source: str | None = Field(default=None, max_length=NAME)
    contact_name: str | None = Field(default=None, max_length=NAME)
    contact_email: EmailStr | None = None
    follow_up_date: datetime | None = None
    reminder_note: str | None = None
    notes: str | None = None

    model_config = {"use_enum_values": True}

    @field_validator("follow_up_date")
    @classmethod
    def _follow_up_utc(cls, value: datetime | None) -> datetime | None:
        return _utc(value)


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, max_length=NAME)
    title: str | None = Field(default=None, max_length=NAME)
    status: JobStatus | None = None
    job_id: int | None = None
    source: str | None = Field(default=None, max_length=NAME)
    contact_name: str | None = Field(default=None, max_length=NAME)
    contact_email: EmailStr | None = None
    follow_up_date: datetime | None = None
    reminder_note: str | None = None
    notes: str | None = None

    model_config = {"use_enum_values": True}

    @field_validator("follow_up_date")
    @classmethod
    def _follow_up_utc(cls, value: datetime | None) -> datetime | None:
        return _utc(value)


class ApplicationOut(ApplicationCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("created_at", "updated_at")
    @classmethod
    def _timestamps_utc(cls, value: datetime) -> datetime:
        return _utc(value)


class AnalyticsOut(BaseModel):
    total_jobs: int
    total_applications: int
    status_counts: dict[str, int]
    average_fit_score: int
    follow_ups_due: int


class TailorRequest(BaseModel):
    job_description: str = Field(min_length=1, max_length=20000)
    resume_text: str | None = Field(default=None, max_length=50000)
    max_bullets: int = Field(default=6, ge=1, le=12)


class TailoredBullet(BaseModel):
    text: str
    # The exact resume line the bullet is based on.
    evidence: str
    matched_keywords: list[str]


class RejectedBullet(BaseModel):
    text: str
    reason: str


class TailorResult(BaseModel):
    # "ai" when a model proposed the bullets, "extractive" when they are the
    # resume's own lines ranked for the job.
    source: str
    bullets: list[TailoredBullet]
    rejected: list[RejectedBullet]
    # Technologies the job asks for that the resume never mentions. Shown as
    # gaps; never written into a bullet.
    missing_keywords: list[str]
    generated: int
    unsupported_rate: float

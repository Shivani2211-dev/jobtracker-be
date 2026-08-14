from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class JobStatus(str, Enum):
    applied = "Applied"
    interview = "Interview"
    offer = "Offer"
    rejected = "Rejected"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=6)


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


class ResumeUpdate(BaseModel):
    resume_text: str
    resume_filename: str | None = None


class ResumeParseResult(BaseModel):
    resume_text: str
    summary: str
    skills: list[str]


class JobCreate(BaseModel):
    company: str
    title: str
    description: str
    status: JobStatus = JobStatus.applied
    location: str | None = None
    url: str | None = None
    notes: str | None = None


class JobUpdate(BaseModel):
    company: str | None = None
    title: str | None = None
    description: str | None = None
    status: JobStatus | None = None
    location: str | None = None
    url: str | None = None
    notes: str | None = None


class JobOut(JobCreate):
    id: int
    fit_score: int | None = None
    ai_feedback: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
    company: str
    title: str
    status: JobStatus = JobStatus.applied
    job_id: int | None = None
    source: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    follow_up_date: datetime | None = None
    reminder_note: str | None = None
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    company: str | None = None
    title: str | None = None
    status: JobStatus | None = None
    job_id: int | None = None
    source: str | None = None
    contact_name: str | None = None
    contact_email: EmailStr | None = None
    follow_up_date: datetime | None = None
    reminder_note: str | None = None
    notes: str | None = None


class ApplicationOut(ApplicationCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsOut(BaseModel):
    total_jobs: int
    total_applications: int
    status_counts: dict[str, int]
    average_fit_score: int
    follow_ups_due: int

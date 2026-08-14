from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Job, User
from app.schemas.schemas import (
    AIAnalysisResult,
    AnalyzeRequest,
    CoverLetterRequest,
    CoverLetterResult,
    InterviewQuestionResult,
)
from app.services.ai_service import analyze_resume_fit, generate_cover_letter, generate_interview_questions

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("", response_model=AIAnalysisResult)
async def analyze(payload: AnalyzeRequest, current_user: User = Depends(get_current_user)):
    return await analyze_resume_fit(payload.job_description, payload.resume_text or current_user.resume_text)


@router.post("/job/{job_id}", response_model=AIAnalysisResult)
async def analyze_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = await analyze_resume_fit(job.description, current_user.resume_text)
    job.fit_score = result.fit_score
    job.ai_feedback = result.summary
    db.commit()
    return result


@router.post("/cover-letter", response_model=CoverLetterResult)
async def cover_letter(payload: CoverLetterRequest, current_user: User = Depends(get_current_user)):
    return await generate_cover_letter(
        payload.job_description,
        payload.company,
        payload.title,
        payload.resume_text or current_user.resume_text,
    )


@router.post("/interview-questions", response_model=InterviewQuestionResult)
async def interview_questions(payload: AnalyzeRequest, current_user: User = Depends(get_current_user)):
    return await generate_interview_questions(payload.job_description, payload.resume_text or current_user.resume_text)

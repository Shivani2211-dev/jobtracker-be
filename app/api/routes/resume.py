from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import ResumeParseResult, ResumeUpdate, UserOut
from app.services.ai_service import parse_resume_text

router = APIRouter(prefix="/resume", tags=["resume"])


@router.get("", response_model=UserOut)
def get_resume(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("", response_model=UserOut)
def update_resume(payload: ResumeUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    parsed = parse_resume_text(payload.resume_text)
    current_user.resume_text = payload.resume_text
    current_user.resume_filename = payload.resume_filename
    current_user.resume_summary = parsed.summary
    current_user.resume_skills = ", ".join(parsed.skills)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/parse", response_model=ResumeParseResult)
async def parse_resume(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    return parse_resume_text(text)


@router.post("/upload", response_model=UserOut)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    parsed = parse_resume_text(text)
    current_user.resume_text = text
    current_user.resume_filename = file.filename
    current_user.resume_summary = parsed.summary
    current_user.resume_skills = ", ".join(parsed.skills)
    db.commit()
    db.refresh(current_user)
    return current_user

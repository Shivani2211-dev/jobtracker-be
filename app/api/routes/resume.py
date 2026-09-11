from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import ResumeParseResult, ResumeUpdate, UserOut
from app.services.ai_service import parse_resume_text

router = APIRouter(prefix="/resume", tags=["resume"])


def save_resume(db: Session, user: User, text: str, filename: str | None) -> User:
    """Store the resume and its parsed summary and skills together, so they
    can never disagree with each other."""
    parsed = parse_resume_text(text)
    user.resume_text = text
    user.resume_filename = (filename or "")[:255] or None
    user.resume_summary = parsed.summary
    user.resume_skills = ", ".join(parsed.skills)
    db.commit()
    db.refresh(user)
    return user


async def read_text_upload(file: UploadFile) -> str:
    """Accept plain-text resumes only, up to the size limit.

    The old handler decoded any upload with errors="ignore", so a PDF was saved
    as binary garbage and then analysed as if it were a resume."""
    data = await file.read(settings.max_resume_bytes + 1)
    if len(data) > settings.max_resume_bytes:
        raise HTTPException(status_code=413, detail="Resume file is too large (1 MB limit).")
    if b"\x00" in data:
        raise HTTPException(
            status_code=415, detail="Upload a plain-text resume (.txt or .md). PDF and Word files aren't supported."
        )
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="Upload a plain-text resume (.txt or .md) saved as UTF-8.") from None


@router.get("", response_model=UserOut)
def get_resume(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("", response_model=UserOut)
def update_resume(payload: ResumeUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return save_resume(db, current_user, payload.resume_text, payload.resume_filename)


@router.post("/parse", response_model=ResumeParseResult)
async def parse_resume(file: UploadFile = File(...), _user: User = Depends(get_current_user)):
    # This used to be open to anyone, logged in or not.
    return parse_resume_text(await read_text_upload(file))


@router.post("/upload", response_model=UserOut)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    text = await read_text_upload(file)
    return save_resume(db, current_user, text, file.filename)

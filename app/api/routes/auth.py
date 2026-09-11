from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.resume import save_resume
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas.schemas import LoginRequest, ResumeUpdate, Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _find_user(db: Session, email: str) -> User | None:
    # The schemas lowercase incoming emails; lower() here also matches accounts
    # created before that, when "Name@x.com" and "name@x.com" were different users.
    return db.query(User).filter(func.lower(User.email) == email.lower()).first()


@router.post("/register", response_model=Token)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if _find_user(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, full_name=payload.full_name, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(str(user.id)), "user": user}


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = _find_user(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return {"access_token": create_access_token(str(user.id)), "user": user}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/resume", response_model=UserOut)
def update_resume(payload: ResumeUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Same as PUT /resume. This path used to save the text but leave the parsed
    # summary and skills describing the previous resume.
    return save_resume(db, current_user, payload.resume_text, payload.resume_filename)

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Application, Job, User
from app.schemas.schemas import AnalyticsOut, ApplicationCreate, ApplicationOut, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Application).filter(Application.user_id == current_user.id).order_by(Application.updated_at.desc()).all()


@router.post("", response_model=ApplicationOut)
def create_application(payload: ApplicationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump(mode="json")
    if payload.job_id:
        job = db.query(Job).filter(Job.id == payload.job_id, Job.user_id == current_user.id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    application = Application(**data, user_id=current_user.id)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = db.query(Application).filter(Application.id == application_id, Application.user_id == current_user.id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    for key, value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(application, key, value)
    db.commit()
    db.refresh(application)
    return application


@router.delete("/{application_id}")
def delete_application(application_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id, Application.user_id == current_user.id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(application)
    db.commit()
    return {"ok": True}


@router.get("/analytics/summary", response_model=AnalyticsOut)
def analytics_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.user_id == current_user.id).all()
    applications = db.query(Application).filter(Application.user_id == current_user.id).all()
    status_counts: dict[str, int] = {}
    for item in applications:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
    scored = [job.fit_score for job in jobs if job.fit_score is not None]
    now = datetime.now(timezone.utc)
    due = [item for item in applications if item.follow_up_date and item.follow_up_date <= now]
    return AnalyticsOut(
        total_jobs=len(jobs),
        total_applications=len(applications),
        status_counts=status_counts,
        average_fit_score=round(sum(scored) / len(scored)) if scored else 0,
        follow_ups_due=len(due),
    )

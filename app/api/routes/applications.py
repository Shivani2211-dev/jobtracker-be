from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Application, Job, User
from app.schemas.schemas import AnalyticsOut, ApplicationCreate, ApplicationOut, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["applications"])


def _require_own_job(db: Session, job_id: int | None, user: User) -> None:
    """An application may only point at a job its owner created."""
    if job_id is None:
        return
    if not db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first():
        raise HTTPException(status_code=404, detail="Job not found")


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes even for timezone-aware columns. Comparing
    # one with an aware "now" raised TypeError and made analytics a 500.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("", response_model=list[ApplicationOut])
def list_applications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Application).filter(Application.user_id == current_user.id).order_by(Application.updated_at.desc()).all()


@router.post("", response_model=ApplicationOut)
def create_application(payload: ApplicationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump()
    _require_own_job(db, payload.job_id, current_user)
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
    changes = payload.model_dump(exclude_unset=True)
    if "job_id" in changes:
        _require_own_job(db, changes["job_id"], current_user)
    for key, value in changes.items():
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
    due = [item for item in applications if item.follow_up_date and _as_utc(item.follow_up_date) <= now]
    return AnalyticsOut(
        total_jobs=len(jobs),
        total_applications=len(applications),
        status_counts=status_counts,
        average_fit_score=round(sum(scored) / len(scored)) if scored else 0,
        follow_ups_due=len(due),
    )

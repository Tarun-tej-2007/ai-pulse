from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..utils import maturity_level
from ..services.practice_plan import get_or_create_plan, toggle_activity_status

router = APIRouter(prefix="/practice-plan", tags=["practice-plan"])


class ToggleIn(BaseModel):
    activity_key: str
    completed: bool


@router.get("/me")
def get_my_practice_plan(
    m: models.Membership = Depends(current_membership),
    db: Session = Depends(get_db),
):
    """Returns the authenticated employee's personalized AI Practice Plan."""
    rows = db.query(models.Response).filter_by(membership_id=m.id).all()
    if not rows:
        return {
            "has_assessment": False,
            "level": "Not assessed",
            "message": "Complete your AI diagnostic first to generate a personalized practice plan.",
            "activities": [],
        }

    scores = [r.score for r in rows if r.score is not None]
    avg = sum(scores) / len(scores) if scores else None
    level = maturity_level(avg)
    risks = sorted({f for r in rows for f in (r.flags or [])})

    activities = get_or_create_plan(m, db, level, risks)
    return {
        "has_assessment": True,
        "level": level,
        "activities": activities,
    }


@router.post("/me/toggle")
def toggle_activity(
    body: ToggleIn,
    m: models.Membership = Depends(current_membership),
    db: Session = Depends(get_db),
):
    """Updates completion state for an activity in the authenticated employee's practice plan."""
    # Ensure employee has completed the assessment
    rows = db.query(models.Response).filter_by(membership_id=m.id).all()
    if not rows:
        raise HTTPException(400, "Cannot complete practice activities before taking the diagnostic.")

    try:
        updated = toggle_activity_status(m, body.activity_key, body.completed, db)
        return updated
    except ValueError as e:
        raise HTTPException(400, str(e))

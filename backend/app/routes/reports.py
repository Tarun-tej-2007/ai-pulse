from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..utils import maturity_level

router = APIRouter(prefix="/reports", tags=["reports"])

NEXT_STEPS = {
    "support": ["Use AI to draft first replies, then edit", "Summarise long ticket threads before escalating", "Never paste customer details into public chatbots"],
    "engineering": ["Use a code assistant for tests and refactors", "Review every AI suggestion before merging", "Keep secrets and customer data out of prompts"],
    "sales": ["Draft outreach emails with AI and personalise them", "Summarise call notes into CRM updates", "Check AI-written claims before sending"],
    "manager": ["Agree an AI usage policy with your team", "Pick one workflow per quarter to improve with AI", "Track time saved, not tool licences"],
}


@router.get("/me")
def my_report(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    rows = db.query(models.Response).filter_by(membership_id=m.id).all()
    scores = [r.score for r in rows if r.score is not None]
    avg = sum(scores) / len(scores) if scores else None
    flags = sorted({f for r in rows for f in (r.flags or [])})
    has_data = len(rows) > 0

    return {
        "name": m.user.name,
        "organization": m.org.name,
        "answered": len(rows),
        "average_score": round(avg, 2) if avg is not None else None,
        "level": maturity_level(avg),
        "risks": flags,
        "next_steps": NEXT_STEPS.get(m.job_role, NEXT_STEPS["manager"]) if has_data else [],
    }


@router.delete("/me")
def delete_my_report(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    """Right to delete: permanently removes all assessment answers and generated report for the authenticated employee."""
    try:
        deleted_count = (
            db.query(models.Response)
            .filter_by(membership_id=m.id)
            .delete(synchronize_session="fetch")
        )
        db.query(models.PracticePlanItem).filter_by(membership_id=m.id).delete(synchronize_session="fetch")
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to delete assessment data: {e}")

    return {
        "deleted": deleted_count,
        "message": (
            "Assessment and report data permanently deleted."
            if deleted_count > 0 else "No assessment data found."
        ),
    }

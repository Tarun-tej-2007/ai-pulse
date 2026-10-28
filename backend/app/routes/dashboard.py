from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


PRIVACY_THRESHOLD = 5


def level_for(avg):
    if avg is None:
        return "Not assessed"
    if avg < 1.5:
        return "Beginner"
    if avg < 2.5:
        return "Exploring"
    if avg < 3.5:
        return "Practitioner"
    return "Leader"


@router.get("")
def org_dashboard(
    org_id: int | None = None,
    m: models.Membership = Depends(current_membership),
    db: Session = Depends(get_db),
):
    if m.role != "admin":
        raise HTTPException(403, "Admins only")

    # Enforce multi-tenant data isolation: an admin can only view their active organization
    if org_id is not None and org_id != m.org_id:
        raise HTTPException(403, "Access forbidden: cannot view another organization's dashboard")

    target_org_id = m.org_id
    org = db.get(models.Organization, target_org_id)
    if not org:
        raise HTTPException(404, "Organization not found")

    members = db.query(models.Membership).filter_by(org_id=target_org_id).all()
    departments = []
    all_flags = {}
    total_org_responded = 0

    for dept in org.departments:
        dept_members = [x for x in members if x.department_id == dept.id]
        member_averages = []
        dept_flags = {}

        for dm in dept_members:
            rows = db.query(models.Response).filter_by(membership_id=dm.id).all()
            valid_scores = [r.score for r in rows if r.score is not None]
            if valid_scores:
                member_avg = sum(valid_scores) / len(valid_scores)
                member_averages.append(member_avg)
                for r in rows:
                    for f in r.flags or []:
                        dept_flags[f] = dept_flags.get(f, 0) + 1

        responded = len(member_averages)
        total_org_responded += responded
        is_suppressed = responded < PRIVACY_THRESHOLD

        if is_suppressed:
            departments.append({
                "department": dept.name,
                "employees": len(dept_members),
                "responded": responded,
                "suppressed": True,
                "average_score": None,
                "level": "Protected (< 5 responses)" if responded > 0 else "Not assessed",
                "privacy_note": (
                    "Scores withheld to protect employee privacy (minimum 5 responses required)."
                    if responded > 0 else "No responses recorded yet."
                ),
            })
        else:
            dept_avg = sum(member_averages) / len(member_averages)
            departments.append({
                "department": dept.name,
                "employees": len(dept_members),
                "responded": responded,
                "suppressed": False,
                "average_score": round(dept_avg, 2),
                "level": level_for(dept_avg),
                "privacy_note": None,
            })
            # Only include flags from departments meeting privacy threshold into org risks
            for f, count in dept_flags.items():
                all_flags[f] = all_flags.get(f, 0) + count

    return {
        "organization": org.name,
        "departments": departments,
        "top_risks": sorted(all_flags.items(), key=lambda kv: -kv[1])[:5],
        "privacy_threshold": PRIVACY_THRESHOLD,
    }

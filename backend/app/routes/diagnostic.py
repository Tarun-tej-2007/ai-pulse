from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..auth import current_membership
from ..services.questions import questions_for, load_questions
from ..services.scoring import score_open_answer

from ..services.llm import AIServiceError

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


class AnswerIn(BaseModel):
    question_id: str
    answer: str


class SubmitIn(BaseModel):
    answers: list[AnswerIn]


@router.get("/questions")
def get_questions(m: models.Membership = Depends(current_membership)):
    qs = questions_for(m.job_role, m.seniority)
    # don't leak scoring points to the client
    return [
        {k: v for k, v in q.items() if k != "points"} | (
            {"options": [o["text"] for o in q["options"]]} if q["type"] == "mcq" else {}
        )
        for q in qs
    ]


@router.post("/submit")
def submit(body: SubmitIn, m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    if not body.answers:
        raise HTTPException(400, "Answers cannot be empty")

    bank = {q["id"]: q for q in load_questions()}
    new_responses = []

    try:
        for a in body.answers:
            q = bank.get(a.question_id)
            if not q:
                raise HTTPException(400, f"Unknown question {a.question_id}")

            resp = models.Response(membership_id=m.id, question_id=q["id"], answer=a.answer)
            if q["type"] == "mcq":
                option = next((o for o in q.get("options", []) if o["text"] == a.answer), None)
                if option is None:
                    raise HTTPException(400, f"Invalid option for {q['id']}")
                resp.score = option["points"]
            else:
                result = score_open_answer(q["text"], a.answer)
                resp.score = result["score"]
                resp.reason = result["reason"]
                resp.flags = result["flags"]

            new_responses.append(resp)

        # Atomic update: replace existing answers for this membership to prevent duplicates
        submitted_qids = [r.question_id for r in new_responses]
        db.query(models.Response).filter(
            models.Response.membership_id == m.id,
            models.Response.question_id.in_(submitted_qids),
        ).delete(synchronize_session="fetch")

        for r in new_responses:
            db.add(r)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except AIServiceError as e:
        db.rollback()
        raise HTTPException(502, f"AI scoring failed: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to submit answers: {e}")

    return {"saved": len(new_responses)}


@router.delete("/me")
def delete_my_diagnostic(m: models.Membership = Depends(current_membership), db: Session = Depends(get_db)):
    """Right to delete: permanently removes all assessment answers and generated report for the authenticated employee."""
    try:
        deleted_count = (
            db.query(models.Response)
            .filter_by(membership_id=m.id)
            .delete(synchronize_session="fetch")
        )
        # Also clean up dependent practice plan items
        db.query(models.PracticePlanItem).filter_by(membership_id=m.id).delete(synchronize_session="fetch")
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to delete assessment data: {e}")

    return {
        "deleted": deleted_count,
        "message": (
            "Assessment data successfully deleted."
            if deleted_count > 0 else "No existing assessment data to delete."
        ),
    }

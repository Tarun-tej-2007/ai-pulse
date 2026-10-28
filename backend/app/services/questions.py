import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "questions.json")


SENIORITY_RANKS = {
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "lead": 4,
}


def load_questions():
    with open(_PATH, encoding="utf-8") as f:
        return json.load(f)


def questions_for(job_role: str, seniority: str):
    """Common questions for everyone + questions for this job role, filtered by seniority."""
    result = []
    clean_role = str(job_role).strip().lower() if job_role else ""
    user_rank = SENIORITY_RANKS.get(str(seniority).strip().lower(), 0) if seniority else 0

    for q in load_questions():
        roles = q.get("roles", [])
        if roles != ["all"] and clean_role not in roles:
            continue

        min_sen = q.get("min_seniority")
        if min_sen is not None:
            # Question requires a minimum seniority level
            min_rank = SENIORITY_RANKS.get(str(min_sen).strip().lower(), 99)
            if user_rank < min_rank:
                continue

        result.append(q)
    return result

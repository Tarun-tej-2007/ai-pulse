import json
import re

from . import llm
from .llm import AIServiceError

ALLOWED_FLAGS = {
    "customer_data_shared",
    "confidential_data_shared",
    "unreviewed_output",
    "policy_unaware",
}


class AIValidationError(AIServiceError):
    """Raised when the AI output cannot be parsed or fails validation."""
    pass


def _extract_json_string(raw: str) -> str:
    """Strips markdown code blocks, whitespace, or surrounding text to find the JSON object."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening ``` or ```json
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # Drop closing ```
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # If still not starting with {, search for the first JSON object using regex
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

    return text


def score_open_answer(question_text: str, answer: str) -> dict:
    """Scores an open-ended answer, enforcing strict validation on model output."""
    clean_answer = str(answer or "").strip()
    if not clean_answer:
        raise AIValidationError("Answer cannot be empty.")

    raw = llm.score_answer(question_text, clean_answer)
    json_str = _extract_json_string(raw)

    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        raise AIValidationError(f"Malformed JSON from AI model: {e}") from e

    if not isinstance(data, dict):
        raise AIValidationError("Expected JSON object from AI model.")

    # 1. Validate Score
    raw_score = data.get("score")
    if raw_score is None:
        raise AIValidationError("Missing required 'score' field in AI response.")

    try:
        score = float(raw_score)
    except (ValueError, TypeError):
        raise AIValidationError(f"Invalid non-numeric score value: {raw_score!r}")

    if not (1.0 <= score <= 5.0):
        raise AIValidationError(f"Score {score} is outside allowable range (1.0 - 5.0).")

    # 2. Validate Reason
    reason = data.get("reason")
    if not reason or not isinstance(reason, str) or not reason.strip():
        raise AIValidationError("Missing or invalid 'reason' explanation in AI response.")
    clean_reason = reason.strip()[:500]

    # 3. Validate Flags
    raw_flags = data.get("flags")
    valid_flags = []
    if isinstance(raw_flags, list):
        for f in raw_flags:
            if isinstance(f, str) and f.strip() in ALLOWED_FLAGS:
                valid_flags.append(f.strip())

    return {
        "score": round(score, 1),
        "reason": clean_reason,
        "flags": sorted(set(valid_flags)),
    }

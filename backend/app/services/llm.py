"""Thin wrapper around the LLM used to score open-ended answers.

AI_MODE=mock  -> returns canned responses from data/mock_ai_responses.json
AI_MODE=live  -> calls an OpenAI-compatible chat completions endpoint
"""
import hashlib
import json
import os

import httpx

from ..config import AI_MODE, LLM_API_URL, LLM_API_KEY, LLM_MODEL

_MOCK_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mock_ai_responses.json")

PROMPT = """You are scoring how well an employee uses AI at work.
Rubric: 1 = no AI use, 2 = occasional basic use, 3 = regular use for simple tasks,
4 = regular, thoughtful use with review of outputs, 5 = advanced use that changes how the work is done.
Flag risks using only these labels: customer_data_shared, confidential_data_shared, unreviewed_output, policy_unaware.
Answer the question: {question}
Employee's answer: {answer}
Return JSON: {{"score": <1-5>, "reason": "<one sentence>", "flags": [<labels>]}}"""


class AIServiceError(Exception):
    """Base exception for AI scoring failures."""
    pass


class AIConfigurationError(AIServiceError):
    """Raised when LLM configuration is missing or invalid."""
    pass


class AITimeoutError(AIServiceError):
    """Raised when the LLM provider call times out."""
    pass


class AIProviderError(AIServiceError):
    """Raised when the LLM provider returns an HTTP error or is unreachable."""
    pass


def _mock(answer: str) -> str:
    if not os.path.exists(_MOCK_PATH):
        raise AIServiceError("Mock AI responses file not found.")
    try:
        with open(_MOCK_PATH, encoding="utf-8") as f:
            canned = json.load(f)
    except Exception as e:
        raise AIServiceError(f"Failed to load mock responses: {e}")
    if not canned:
        raise AIServiceError("Mock responses list is empty.")
    idx = int(hashlib.md5(answer.encode("utf-8")).hexdigest(), 16) % len(canned)
    return canned[idx]


def score_answer(question: str, answer: str) -> str:
    """Returns the raw text the model produced, handling timeouts, missing config, and provider errors."""
    clean_answer = str(answer or "").strip()
    clean_question = str(question or "").strip()

    if AI_MODE == "mock":
        return _mock(clean_answer)

    if not LLM_API_URL:
        raise AIConfigurationError("LLM_API_URL is not configured.")

    # Avoid format string injection by constructing messages cleanly
    user_prompt = (
        f"{PROMPT.split('Answer the question:')[0].strip()}\n\n"
        f"Answer the question: {clean_question}\n"
        f"Employee's answer: {clean_answer}\n"
        f'Return JSON: {{"score": <1-5>, "reason": "<one sentence>", "flags": [<labels>]}}'
    )

    headers = {}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                LLM_API_URL,
                headers=headers,
                json={
                    "model": LLM_MODEL or "default-model",
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
            r.raise_for_status()
            data = r.json()
            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                raise AIProviderError("AI provider returned response without choices.")
            content = choices[0].get("message", {}).get("content")
            if not content:
                raise AIProviderError("AI provider returned empty message content.")
            return content
    except httpx.TimeoutException as e:
        raise AITimeoutError(f"AI provider request timed out: {e}") from e
    except httpx.HTTPStatusError as e:
        raise AIProviderError(f"AI provider HTTP {e.response.status_code}: {e.response.text[:200]}") from e
    except httpx.RequestError as e:
        raise AIProviderError(f"Network error connecting to AI provider: {e}") from e

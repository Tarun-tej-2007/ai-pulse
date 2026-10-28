import json
import pytest
from app.services import scoring, llm
from app.services.scoring import score_open_answer, AIValidationError
from app.services.llm import AIServiceError, AITimeoutError, AIProviderError
from tests.conftest import login


def test_score_valid_json_response(monkeypatch):
    sample_response = '{"score": 4, "reason": "Uses AI weekly with critical review.", "flags": ["unreviewed_output"]}'
    monkeypatch.setattr(llm, "score_answer", lambda q, a: sample_response)

    res = score_open_answer("How do you use AI?", "I use ChatGPT for drafts and check them.")
    assert res["score"] == 4.0
    assert res["reason"] == "Uses AI weekly with critical review."
    assert res["flags"] == ["unreviewed_output"]


def test_score_markdown_fenced_json(monkeypatch):
    sample_response = '```json\n{"score": 3.5, "reason": "Good structured usage.", "flags": []}\n```'
    monkeypatch.setattr(llm, "score_answer", lambda q, a: sample_response)

    res = score_open_answer("How do you use AI?", "Structured prompts daily.")
    assert res["score"] == 3.5
    assert res["reason"] == "Good structured usage."
    assert res["flags"] == []


def test_score_rejects_out_of_range(monkeypatch):
    # Score 7 is out of 1-5 range
    monkeypatch.setattr(llm, "score_answer", lambda q, a: '{"score": 7, "reason": "Super advanced.", "flags": []}')
    with pytest.raises(AIValidationError) as exc:
        score_open_answer("Q", "Answer")
    assert "outside allowable range" in str(exc.value).lower()

    # Score 0 is out of 1-5 range
    monkeypatch.setattr(llm, "score_answer", lambda q, a: '{"score": 0, "reason": "Zero usage.", "flags": []}')
    with pytest.raises(AIValidationError):
        score_open_answer("Q", "Answer")


def test_score_rejects_non_numeric_score(monkeypatch):
    monkeypatch.setattr(llm, "score_answer", lambda q, a: '{"score": "four", "reason": "Good.", "flags": []}')
    with pytest.raises(AIValidationError) as exc:
        score_open_answer("Q", "Answer")
    assert "invalid non-numeric score" in str(exc.value).lower()


def test_score_rejects_missing_reason(monkeypatch):
    monkeypatch.setattr(llm, "score_answer", lambda q, a: '{"score": 3, "flags": []}')
    with pytest.raises(AIValidationError) as exc:
        score_open_answer("Q", "Answer")
    assert "missing or invalid 'reason'" in str(exc.value).lower()


def test_score_filters_unrecognized_flags(monkeypatch):
    monkeypatch.setattr(
        llm,
        "score_answer",
        lambda q, a: '{"score": 2, "reason": "Basic.", "flags": ["customer_data_shared", "hallucination_flag", "made_up"]}',
    )
    res = score_open_answer("Q", "Answer")
    # Only allowed flags should be preserved
    assert res["flags"] == ["customer_data_shared"]


def test_score_rejects_empty_answer():
    with pytest.raises(AIValidationError) as exc:
        score_open_answer("Q", "   ")
    assert "answer cannot be empty" in str(exc.value).lower()


def test_ai_provider_error_rolls_back_submission(client, monkeypatch):
    headers, _ = login(client, "dev@northwind.test", "Northwind Logistics")

    # Simulate AI service failure during open question scoring
    def mock_fail(q, a):
        raise AITimeoutError("LLM call timed out after 15s")

    monkeypatch.setattr(llm, "score_answer", mock_fail)

    payload = {
        "answers": [
            {"question_id": "common-freq", "answer": "Daily"},
            {"question_id": "common-open", "answer": "I write code with Copilot."},
        ]
    }
    r = client.post("/diagnostic/submit", json=payload, headers=headers)
    assert r.status_code == 502
    assert "ai scoring failed" in r.json()["detail"].lower()

    # Verify no partial or corrupted records were saved
    r_me = client.get("/reports/me", headers=headers)
    assert r_me.json()["answered"] == 0

from app.services.questions import questions_for


def ids(qs):
    return {q["id"] for q in qs}


def test_everyone_gets_common_questions():
    got = ids(questions_for("sales", "junior"))
    assert {"common-freq", "common-policy", "common-data", "common-review", "common-open"} <= got


def test_junior_engineer_does_not_get_senior_questions():
    got = ids(questions_for("engineering", "junior"))
    assert "eng-assistant" in got
    assert "eng-review" not in got
    assert "eng-arch" not in got


def test_senior_support_gets_escalation_question():
    assert "sup-escalation" in ids(questions_for("support", "senior"))


def test_lead_manager_gets_policy_questions():
    got = ids(questions_for("manager", "lead"))
    assert "mgr-policy" in got
    assert "mgr-open" in got
    assert "mgr-adoption" in got


def test_mid_engineer_gets_mid_but_not_senior():
    got = ids(questions_for("engineering", "mid"))
    assert "eng-assistant" in got
    assert "eng-review" in got
    assert "eng-arch" not in got


def test_role_specific_question_filtering():
    support_qs = ids(questions_for("support", "lead"))
    engineering_qs = ids(questions_for("engineering", "lead"))
    sales_qs = ids(questions_for("sales", "lead"))
    manager_qs = ids(questions_for("manager", "lead"))

    # Support doesn't get engineering or sales
    assert "eng-assistant" not in support_qs
    assert "sales-outreach" not in support_qs
    # Engineering doesn't get support or sales
    assert "sup-drafts" not in engineering_qs
    assert "sales-outreach" not in engineering_qs
    # Manager doesn't get engineering
    assert "eng-arch" not in manager_qs


def test_invalid_seniority_does_not_leak_restricted_questions():
    got = ids(questions_for("engineering", "unknown_seniority"))
    common_ids = {"common-freq", "common-policy", "common-data", "common-review", "common-open"}
    # Must get common questions
    assert common_ids <= got
    # Must NOT get restricted questions
    assert "eng-assistant" not in got
    assert "eng-review" not in got
    assert "eng-arch" not in got


def test_none_and_empty_inputs_handled_safely():
    got_none = ids(questions_for(None, None))
    common_ids = {"common-freq", "common-policy", "common-data", "common-review", "common-open"}
    assert common_ids == got_none

    got_empty = ids(questions_for("", ""))
    assert common_ids == got_empty

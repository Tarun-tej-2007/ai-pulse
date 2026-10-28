import pytest
from app import models, db
from tests.conftest import login


def _add_completed_assessment(session, email, org_name, dept_name, score=4.0, flags=None):
    """Helper to add completed response records for testing privacy thresholds."""
    user = session.query(models.User).filter_by(email=email).first()
    if not user:
        user = models.User(name=email.split("@")[0].title(), email=email, password_hash="test")
        session.add(user)
        session.flush()

    org = session.query(models.Organization).filter_by(name=org_name).first()
    dept = session.query(models.Department).filter_by(name=dept_name, org_id=org.id).first()

    membership = (
        session.query(models.Membership)
        .filter_by(user_id=user.id, org_id=org.id)
        .first()
    )
    if not membership:
        membership = models.Membership(
            user_id=user.id,
            org_id=org.id,
            department_id=dept.id,
            role="employee",
            job_role="engineering",
            seniority="mid",
        )
        session.add(membership)
        session.flush()

    session.add(models.Response(
        membership_id=membership.id,
        question_id="common-freq",
        answer="Daily",
        score=score,
        reason="Test score",
        flags=flags or [],
    ))
    session.commit()
    return membership


def test_small_group_privacy_thresholds(client):
    """Test thresholds of 0, 1, 4, 5, and 6 completed assessments."""
    admin_headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    session = db.SessionLocal()

    try:
        # Clear existing responses in Northwind to test exact counts
        nw = session.query(models.Organization).filter_by(name="Northwind Logistics").first()
        nw_mids = [m.id for m in session.query(models.Membership).filter_by(org_id=nw.id).all()]
        session.query(models.Response).filter(models.Response.membership_id.in_(nw_mids)).delete(synchronize_session=False)
        session.commit()

        # 1. Zero completed assessments in Engineering
        r0 = client.get("/dashboard", headers=admin_headers)
        assert r0.status_code == 200
        eng0 = next(d for d in r0.json()["departments"] if d["department"] == "Engineering")
        assert eng0["responded"] == 0
        assert eng0["suppressed"] is True
        assert eng0["average_score"] is None
        assert eng0["level"] == "Not assessed"

        # 2. Add 1 completed assessment
        _add_completed_assessment(session, "user1@northwind.test", "Northwind Logistics", "Engineering", score=4.0)
        r1 = client.get("/dashboard", headers=admin_headers)
        eng1 = next(d for d in r1.json()["departments"] if d["department"] == "Engineering")
        assert eng1["responded"] == 1
        assert eng1["suppressed"] is True
        assert eng1["average_score"] is None
        assert "protected" in eng1["level"].lower()

        # 3. Add assessments up to 4 completed (threshold - 1)
        _add_completed_assessment(session, "user2@northwind.test", "Northwind Logistics", "Engineering", score=3.0)
        _add_completed_assessment(session, "user3@northwind.test", "Northwind Logistics", "Engineering", score=4.0)
        _add_completed_assessment(session, "user4@northwind.test", "Northwind Logistics", "Engineering", score=3.0)

        r4 = client.get("/dashboard", headers=admin_headers)
        eng4 = next(d for d in r4.json()["departments"] if d["department"] == "Engineering")
        assert eng4["responded"] == 4
        assert eng4["suppressed"] is True
        assert eng4["average_score"] is None
        assert "protected" in eng4["level"].lower()

        # 4. Add the 5th completed assessment (reaches threshold of 5)
        _add_completed_assessment(session, "user5@northwind.test", "Northwind Logistics", "Engineering", score=4.0)
        r5 = client.get("/dashboard", headers=admin_headers)
        eng5 = next(d for d in r5.json()["departments"] if d["department"] == "Engineering")
        assert eng5["responded"] == 5
        assert eng5["suppressed"] is False
        assert eng5["average_score"] is not None
        # Scores: 4.0, 3.0, 4.0, 3.0, 4.0 -> average = 3.6
        assert eng5["average_score"] == 3.6
        assert eng5["level"] == "Leader"

        # 5. Add a 6th completed assessment (above threshold)
        _add_completed_assessment(session, "user6@northwind.test", "Northwind Logistics", "Engineering", score=3.0)
        r6 = client.get("/dashboard", headers=admin_headers)
        eng6 = next(d for d in r6.json()["departments"] if d["department"] == "Engineering")
        assert eng6["responded"] == 6
        assert eng6["suppressed"] is False
        # Scores: 4, 3, 4, 3, 4, 3 -> average = 3.5
        assert eng6["average_score"] == 3.5
    finally:
        session.close()


def test_independent_enforcement_per_department_and_org(client):
    """Verifies that privacy threshold is enforced independently per department."""
    admin_headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    session = db.SessionLocal()

    try:
        # Clear existing responses to test exact isolated counts
        session.query(models.Response).delete()
        session.commit()

        # Give Support 5 respondents and Sales 2 respondents
        for i in range(1, 6):
            _add_completed_assessment(session, f"sup{i}@northwind.test", "Northwind Logistics", "Support", score=3.0)
        for i in range(1, 3):
            _add_completed_assessment(session, f"sal{i}@northwind.test", "Northwind Logistics", "Sales", score=4.0)

        r = client.get("/dashboard", headers=admin_headers)
        assert r.status_code == 200
        depts = {d["department"]: d for d in r.json()["departments"]}

        # Support must be unsuppressed
        assert depts["Support"]["suppressed"] is False
        assert depts["Support"]["average_score"] == 3.0

        # Sales must be suppressed
        assert depts["Sales"]["suppressed"] is True
        assert depts["Sales"]["average_score"] is None
        assert "protected" in depts["Sales"]["level"].lower()
    finally:
        session.close()


def test_incomplete_assessments_do_not_count_towards_threshold(client):
    """Answers with score=None (incomplete/unscored) must not count toward the 5-response threshold."""
    admin_headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    session = db.SessionLocal()

    try:
        session.query(models.Response).delete()
        session.commit()

        # Add 5 memberships in HR, but only 4 have valid scores, 1 has score=None
        for i in range(1, 5):
            _add_completed_assessment(session, f"hr{i}@northwind.test", "Northwind Logistics", "HR", score=3.0)

        # 5th user has an unscored response
        user5 = models.User(name="HR Unscored", email="hr5_unscored@northwind.test", password_hash="test")
        session.add(user5)
        session.flush()
        org = session.query(models.Organization).filter_by(name="Northwind Logistics").first()
        dept = session.query(models.Department).filter_by(name="HR", org_id=org.id).first()
        m5 = models.Membership(user_id=user5.id, org_id=org.id, department_id=dept.id, role="employee", job_role="manager", seniority="senior")
        session.add(m5)
        session.flush()
        session.add(models.Response(membership_id=m5.id, question_id="common-freq", answer="Weekly", score=None))
        session.commit()

        r = client.get("/dashboard", headers=admin_headers)
        hr_dept = next(d for d in r.json()["departments"] if d["department"] == "HR")

        # Must count only 4 completed, and remain suppressed!
        assert hr_dept["responded"] == 4
        assert hr_dept["suppressed"] is True
        assert hr_dept["average_score"] is None
        assert "protected" in hr_dept["level"].lower()
    finally:
        session.close()


def test_deletion_drops_department_below_threshold_re_suppresses_scores(client):
    """When an employee deletes their assessment causing completed count to drop from 5 to 4, scores must immediately be suppressed."""
    admin_headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    session = db.SessionLocal()

    try:
        session.query(models.Response).delete()
        session.commit()

        # Create 5 completed assessments in Sales
        emp5_email = "sal5_delete_me@northwind.test"
        for i in range(1, 5):
            _add_completed_assessment(session, f"sal{i}@northwind.test", "Northwind Logistics", "Sales", score=4.0)

        # 5th employee with known password for login
        u5 = models.User(name="Sales Five", email=emp5_email, password_hash=models.User.__table__.columns.password_hash.type.python_type())
        from app.auth import hash_password
        u5.password_hash = hash_password("pulse123")
        session.add(u5)
        session.flush()
        org = session.query(models.Organization).filter_by(name="Northwind Logistics").first()
        dept = session.query(models.Department).filter_by(name="Sales", org_id=org.id).first()
        m5 = models.Membership(user_id=u5.id, org_id=org.id, department_id=dept.id, role="employee", job_role="sales", seniority="senior")
        session.add(m5)
        session.flush()
        session.add(models.Response(membership_id=m5.id, question_id="common-freq", answer="Daily", score=4.0))
        session.commit()

        # Verify Sales is unsuppressed with 5 respondents
        r_before = client.get("/dashboard", headers=admin_headers)
        sales_before = next(d for d in r_before.json()["departments"] if d["department"] == "Sales")
        assert sales_before["responded"] == 5
        assert sales_before["suppressed"] is False
        assert sales_before["average_score"] == 4.0

        # Now 5th employee deletes their data
        emp5_headers, _ = login(client, emp5_email, "Northwind Logistics")
        del_r = client.delete("/diagnostic/me", headers=emp5_headers)
        assert del_r.status_code == 200

        # Check dashboard again: count must drop to 4, and scores must re-suppress immediately!
        r_after = client.get("/dashboard", headers=admin_headers)
        sales_after = next(d for d in r_after.json()["departments"] if d["department"] == "Sales")
        assert sales_after["responded"] == 4
        assert sales_after["suppressed"] is True
        assert sales_after["average_score"] is None
        assert "protected" in sales_after["level"].lower()
    finally:
        session.close()

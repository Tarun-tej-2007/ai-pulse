import pytest
from tests.conftest import login


def test_practice_plan_generated_for_assessed_employee(client):
    # Priya has answers from seed data with risk 'customer_data_shared'
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    r = client.get("/practice-plan/me", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["has_assessment"] is True
    assert len(data["activities"]) == 3

    # Because Priya has 'customer_data_shared' in flags, the safe redaction activity must be included
    keys = [a["key"] for a in data["activities"]]
    assert "risk_customer_data" in keys

    # Verify activity fields
    first = data["activities"][0]
    assert "title" in first
    assert "area" in first
    assert "exercise" in first
    assert "criterion" in first
    assert first["completed"] is False


def test_practice_plan_toggle_completion(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    # Mark first activity as completed
    toggle_payload = {"activity_key": "risk_customer_data", "completed": True}
    res = client.post("/practice-plan/me/toggle", json=toggle_payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["completed"] is True
    assert res.json()["completed_at"] is not None

    # Fetch plan again and verify persistence
    plan_after = client.get("/practice-plan/me", headers=headers).json()
    act = next(a for a in plan_after["activities"] if a["key"] == "risk_customer_data")
    assert act["completed"] is True
    assert act["completed_at"] is not None

    # Toggle back to incomplete
    res_undo = client.post("/practice-plan/me/toggle", json={"activity_key": "risk_customer_data", "completed": False}, headers=headers)
    assert res_undo.status_code == 200
    assert res_undo.json()["completed"] is False


def test_practice_plan_unassessed_employee(client):
    # Dev Malhotra has not taken the diagnostic in seed data
    headers, _ = login(client, "dev@northwind.test", "Northwind Logistics")

    r = client.get("/practice-plan/me", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["has_assessment"] is False
    assert len(data["activities"]) == 0
    assert "complete your ai diagnostic first" in data["message"].lower()

    # Attempting to toggle activity before assessment must fail
    res_toggle = client.post("/practice-plan/me/toggle", json={"activity_key": "role_engineering", "completed": True}, headers=headers)
    assert res_toggle.status_code == 400


def test_practice_plan_cleared_on_assessment_deletion(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    # Mark an activity completed
    client.post("/practice-plan/me/toggle", json={"activity_key": "risk_customer_data", "completed": True}, headers=headers)

    # Delete assessment
    client.delete("/diagnostic/me", headers=headers)

    # Practice plan should now indicate no assessment
    r_plan = client.get("/practice-plan/me", headers=headers).json()
    assert r_plan["has_assessment"] is False
    assert len(r_plan["activities"]) == 0


def test_leadership_dashboard_does_not_expose_practice_plans(client):
    """Confirm leadership dashboard never exposes private employee practice activities or completion states."""
    admin_headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    emp_headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    # Priya marks an activity complete
    client.post("/practice-plan/me/toggle", json={"activity_key": "risk_customer_data", "completed": True}, headers=emp_headers)

    # Admin fetches dashboard
    r_dash = client.get("/dashboard", headers=admin_headers)
    assert r_dash.status_code == 200
    dash_content = str(r_dash.json())

    # Ensure no practice plan keys or details are leaked
    assert "risk_customer_data" not in dash_content
    assert "practice_plan" not in dash_content
    assert "Safe Prompt Redaction Challenge" not in dash_content

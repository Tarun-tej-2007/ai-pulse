import pytest
from tests.conftest import login


def test_employee_can_delete_assessment_and_report(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    # 1. Verify Priya has existing responses from seed
    r_before = client.get("/reports/me", headers=headers)
    assert r_before.status_code == 200
    assert r_before.json()["answered"] > 0
    assert r_before.json()["average_score"] is not None

    # 2. Priya deletes her assessment
    del_res = client.delete("/diagnostic/me", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] > 0

    # 3. Report is immediately cleared
    r_after = client.get("/reports/me", headers=headers)
    assert r_after.status_code == 200
    data_after = r_after.json()
    assert data_after["answered"] == 0
    assert data_after["average_score"] is None
    assert data_after["level"] == "Not assessed"
    assert data_after["risks"] == []


def test_repeated_deletion_is_idempotent(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    # First delete
    client.delete("/diagnostic/me", headers=headers)

    # Second delete: should succeed safely without error
    del_res2 = client.delete("/diagnostic/me", headers=headers)
    assert del_res2.status_code == 200
    assert del_res2.json()["deleted"] == 0


def test_deletion_immediately_updates_dashboard(client):
    admin_headers, _ = login(client, "asha@northwind.test", "Northwind Logistics")
    emp_headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")

    # Get initial dashboard
    dash1 = client.get("/dashboard", headers=admin_headers).json()
    sup1 = next(d for d in dash1["departments"] if d["department"] == "Support")
    initial_responded = sup1["responded"]
    assert initial_responded >= 1

    # Priya deletes her assessment
    client.delete("/reports/me", headers=emp_headers)

    # Dashboard immediately reflects the reduction in responded count
    dash2 = client.get("/dashboard", headers=admin_headers).json()
    sup2 = next(d for d in dash2["departments"] if d["department"] == "Support")
    assert sup2["responded"] == initial_responded - 1


def test_employee_cannot_delete_another_employee_data(client):
    # Two employees
    headers_priya, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    headers_vikram, _ = login(client, "vikram@northwind.test", "Northwind Logistics")

    # Verify Vikram has responses
    v_report_before = client.get("/reports/me", headers=headers_vikram).json()
    assert v_report_before["answered"] > 0

    # Priya executes delete on her session
    client.delete("/diagnostic/me", headers=headers_priya)

    # Vikram's responses must remain completely intact
    v_report_after = client.get("/reports/me", headers=headers_vikram).json()
    assert v_report_after["answered"] == v_report_before["answered"]
    assert v_report_after["average_score"] == v_report_before["average_score"]

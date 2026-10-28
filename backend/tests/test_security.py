import pytest
from tests.conftest import login


def test_unauthenticated_endpoints_return_401(client):
    endpoints = [
        ("GET", "/diagnostic/questions"),
        ("POST", "/diagnostic/submit"),
        ("DELETE", "/diagnostic/me"),
        ("GET", "/reports/me"),
        ("DELETE", "/reports/me"),
        ("GET", "/dashboard"),
        ("GET", "/practice-plan/me"),
        ("POST", "/practice-plan/me/toggle"),
    ]
    for method, path in endpoints:
        if method == "GET":
            r = client.get(path)
        elif method == "POST":
            r = client.post(path, json={})
        elif method == "DELETE":
            r = client.delete(path)
        assert r.status_code == 401, f"{method} {path} should require authentication"


def test_cannot_select_organization_without_membership(client):
    # Priya is only a member of Northwind Logistics (org_id 1), not Bluepeak Retail (org_id 2)
    r = client.post("/auth/login", json={"email": "priya@northwind.test", "password": "pulse123"})
    assert r.status_code == 200
    token = r.json()["token"]

    # Attempt to select org_id=2 (Bluepeak)
    res = client.post(
        "/auth/select-org",
        json={"org_id": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "not a member" in res.json()["detail"].lower()


def test_employee_cannot_access_dashboard(client):
    headers, _ = login(client, "priya@northwind.test", "Northwind Logistics")
    r = client.get("/dashboard", headers=headers)
    assert r.status_code == 403
    assert "admin" in r.json()["detail"].lower()


def test_multi_org_consultant_role_scoping(client):
    # Ravi Kapoor is:
    # 1. Employee in Northwind Logistics
    # 2. Admin in Bluepeak Retail

    # When Ravi acts as Northwind employee:
    nw_headers, _ = login(client, "ravi@consult.test", "Northwind Logistics")
    r_nw_dash = client.get("/dashboard", headers=nw_headers)
    assert r_nw_dash.status_code == 403  # Must be forbidden as employee

    # Can access questions and reports in Northwind
    r_nw_q = client.get("/diagnostic/questions", headers=nw_headers)
    assert r_nw_q.status_code == 200

    # When Ravi switches to Bluepeak as admin:
    bp_headers, _ = login(client, "ravi@consult.test", "Bluepeak Retail")
    r_bp_dash = client.get("/dashboard", headers=bp_headers)
    assert r_bp_dash.status_code == 200
    assert r_bp_dash.json()["organization"] == "Bluepeak Retail"

    # Even as Bluepeak admin, Ravi cannot access Northwind's dashboard
    r_bp_cross = client.get("/dashboard?org_id=1", headers=bp_headers)
    assert r_bp_cross.status_code == 403


def test_invalid_login_credentials(client):
    r = client.post("/auth/login", json={"email": "priya@northwind.test", "password": "wrongpassword"})
    assert r.status_code == 401
    assert "wrong email or password" in r.json()["detail"].lower()

    r2 = client.post("/auth/login", json={"email": "nonexistent@northwind.test", "password": "pulse123"})
    assert r2.status_code == 401


def test_tampered_or_malformed_tokens_rejected(client):
    # Garbage token
    r1 = client.get("/reports/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r1.status_code == 401
    assert "invalid token" in r1.json()["detail"].lower()

    # Missing Bearer prefix
    r2 = client.get("/reports/me", headers={"Authorization": "Token 12345"})
    assert r2.status_code == 401
    assert "missing token" in r2.json()["detail"].lower()

    # Forged token signed with wrong secret
    import jwt
    forged = jwt.encode({"sub": "1", "org": 1}, "wrong-secret-key", algorithm="HS256")
    r3 = client.get("/reports/me", headers={"Authorization": f"Bearer {forged}"})
    assert r3.status_code == 401
    assert "invalid token" in r3.json()["detail"].lower()


def test_token_without_org_selection_rejected_on_org_endpoints(client):
    # Login produces a user token without an org claim yet
    r_login = client.post("/auth/login", json={"email": "priya@northwind.test", "password": "pulse123"})
    assert r_login.status_code == 200
    user_token = r_login.json()["token"]

    # Calling an endpoint that requires an active org must return 400
    r_rep = client.get("/reports/me", headers={"Authorization": f"Bearer {user_token}"})
    assert r_rep.status_code == 400
    assert "select an organization first" in r_rep.json()["detail"].lower()

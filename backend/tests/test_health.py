from __future__ import annotations


def test_health_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] in ("ok", "degraded")
    assert body["version"]
    assert body["server_time_utc"].endswith("+00:00")

    predictor = body["predictor"]
    assert predictor["mode"] == "rule-based-demo"
    assert predictor["trained_ml_used_for_risk"] is False


def test_health_does_not_claim_a_reliable_model(client):
    body = client.get("/api/health").json()
    assert body["ml_artifact"]["reliable"] is False
    assert "not an official flood-warning system" in body["disclaimer"].lower()


def test_root_lists_endpoints(client):
    body = client.get("/").json()
    assert body["focus_city"].startswith("Chennai")
    for endpoint in (
        "GET /api/health",
        "GET /api/zones",
        "POST /api/assess",
        "GET /api/weather?latitude=..&longitude=..",
        "GET /api/reports",
        "POST /api/reports",
    ):
        assert endpoint in body["endpoints"]

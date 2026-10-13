from __future__ import annotations

VALID = {
    "zone_id": "velachery",
    "latitude": 12.98017,
    "longitude": 80.22285,
    "description": "Knee-deep standing water across the bus stand approach road.",
    "severity": "High",
}


def test_create_and_list_report_round_trip(client):
    created = client.post("/api/reports", json=VALID)
    assert created.status_code == 201
    body = created.json()

    assert body["source"] == "user-submitted"
    assert "Unverified" in body["verification"]
    assert body["zone_name"] == "Velachery"
    assert body["id"]

    listing = client.get("/api/reports").json()
    assert listing["count"] >= 1
    assert listing["source"] == "user-submitted"
    assert "not official incident records" in listing["note"]
    assert any(r["id"] == body["id"] for r in listing["reports"])


def test_reports_filter_by_zone(client):
    client.post("/api/reports", json=VALID)
    other = dict(VALID, zone_id="adyar", latitude=13.00645, longitude=80.25778)
    client.post("/api/reports", json=other)

    filtered = client.get("/api/reports", params={"zone_id": "adyar"}).json()
    assert filtered["count"] == 1
    assert filtered["reports"][0]["zone_id"] == "adyar"


def test_short_description_is_rejected(client):
    response = client.post("/api/reports", json=dict(VALID, description="hi"))
    assert response.status_code == 422


def test_invalid_severity_is_rejected(client):
    response = client.post("/api/reports", json=dict(VALID, severity="Catastrophic"))
    assert response.status_code == 422


def test_out_of_range_coordinates_rejected(client):
    response = client.post("/api/reports", json=dict(VALID, latitude=120.0))
    assert response.status_code == 422


def test_unknown_zone_id_returns_404(client):
    response = client.post("/api/reports", json=dict(VALID, zone_id="nowhere"))
    assert response.status_code == 404
    assert "nowhere" in response.json()["detail"]


def test_personal_information_fields_are_not_accepted(client):
    """No PII field exists, and extra fields are rejected outright."""
    response = client.post("/api/reports", json=dict(VALID, email="someone@example.com"))
    assert response.status_code == 422

    from app.schemas import ReportCreate

    forbidden = {"email", "phone", "name", "reporter_name", "address", "aadhaar"}
    assert forbidden.isdisjoint(ReportCreate.model_fields)


def test_description_is_trimmed(client):
    response = client.post(
        "/api/reports", json=dict(VALID, description="   water on the road   ")
    )
    assert response.status_code == 201
    assert response.json()["description"] == "water on the road"


def test_list_limit_is_bounded(client):
    assert client.get("/api/reports", params={"limit": 0}).status_code == 422
    assert client.get("/api/reports", params={"limit": 9999}).status_code == 422

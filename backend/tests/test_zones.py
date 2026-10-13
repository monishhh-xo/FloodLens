from __future__ import annotations

CHENNAI_BBOX = (12.85, 80.05, 13.25, 80.35)


def test_zones_returns_catalogue(client):
    response = client.get("/api/zones")
    assert response.status_code == 200
    body = response.json()

    assert body["count"] == len(body["zones"])
    assert body["count"] >= 8
    assert body["attributes_illustrative"] is True
    assert "OpenStreetMap" in body["coordinate_source"]
    assert "not verified flood hotspots" in body["illustrative_note"]


def test_every_zone_is_inside_chennai_and_labelled_illustrative(client):
    zones = client.get("/api/zones").json()["zones"]
    lat0, lon0, lat1, lon1 = CHENNAI_BBOX
    for zone in zones:
        assert lat0 <= zone["latitude"] <= lat1, zone["id"]
        assert lon0 <= zone["longitude"] <= lon1, zone["id"]
        assert zone["attributes_illustrative"] is True
        assert zone["illustrative_note"]


def test_baseline_preview_is_computed_and_deterministic(client):
    first = client.get("/api/zones").json()["zones"]
    second = client.get("/api/zones").json()["zones"]

    for a, b in zip(first, second):
        assert a["baseline_demo_risk"] == b["baseline_demo_risk"]

    for zone in first:
        preview = zone["baseline_demo_risk"]
        assert preview["illustrative"] is True
        assert 0 <= preview["score"] <= 100
        assert preview["risk_level"] in ("Low", "Moderate", "High", "Severe")
        assert "Not a live reading" in preview["note"]


def test_baseline_preview_varies_with_zone_attributes(client):
    zones = client.get("/api/zones").json()["zones"]
    scores = {z["baseline_demo_risk"]["score"] for z in zones}
    assert len(scores) > 1, "baseline previews are identical for every zone"

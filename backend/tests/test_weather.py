from __future__ import annotations

CHENNAI = {"latitude": 13.0827, "longitude": 80.2707}


def test_weather_success_reports_source_units_and_time(client, online_weather):
    response = client.get("/api/weather", params=CHENNAI)
    assert response.status_code == 200
    body = response.json()

    assert body["available"] is True
    assert "Open-Meteo" in body["source"]
    assert "Open-Meteo" in body["attribution"]
    assert body["retrieved_at_utc"] is not None
    assert body["units"]["precipitation"] == "mm"
    assert body["summary"]["current_precipitation_mm"] is not None


def test_weather_offline_state_contains_no_invented_values(client, offline_weather):
    response = client.get("/api/weather", params=CHENNAI)
    assert response.status_code == 200
    body = response.json()

    assert body["available"] is False
    assert body["status"] == "unavailable"
    assert body["reason"]
    # The critical guarantee: nothing numeric is fabricated on failure.
    assert body["summary"] is None
    assert body["current"] is None
    assert body["units"] is None
    assert body["retrieved_at_utc"] is None
    assert body["hourly"] == []


def test_assess_rejects_missing_rainfall_when_offline(client, offline_weather):
    response = client.post("/api/assess", json={"zone_id": "velachery"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Live weather is unavailable" in detail
    assert "allow_illustrative_fallback" in detail


def test_assess_uses_labelled_illustrative_fallback_when_opted_in(client, offline_weather):
    response = client.post(
        "/api/assess",
        json={"zone_id": "velachery", "allow_illustrative_fallback": True},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["data_quality"]["rainfall_source"] == "illustrative-defaults"
    assert body["data_quality"]["rainfall_is_live_forecast"] is False
    assert body["data_quality"]["weather_available"] is False
    assert any("NOT live" in note for note in body["data_quality"]["notes"])


def test_assess_uses_live_forecast_when_rainfall_omitted(client, online_weather):
    response = client.post("/api/assess", json={"zone_id": "velachery"})
    assert response.status_code == 200
    body = response.json()

    assert body["data_quality"]["rainfall_source"] == "open-meteo-forecast"
    assert body["data_quality"]["rainfall_is_live_forecast"] is True
    assert body["inputs"]["weather_derived"]["rainfall_mm_1h"] == 4.5
    assert any("forecast total" in note for note in body["data_quality"]["notes"])


def test_weather_requires_coordinates(client):
    assert client.get("/api/weather").status_code == 422
    assert client.get("/api/weather", params={"latitude": 13.0}).status_code == 422


def test_weather_rejects_out_of_range_coordinates(client):
    assert client.get(
        "/api/weather", params={"latitude": 999.0, "longitude": 80.0}
    ).status_code == 422
    assert client.get(
        "/api/weather", params={"latitude": 13.0, "longitude": -900.0}
    ).status_code == 422

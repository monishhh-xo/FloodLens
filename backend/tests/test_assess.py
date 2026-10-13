from __future__ import annotations


def _assess(client, **overrides):
    payload = {"zone_id": "velachery", "rainfall_mm_1h": 45.0, "rainfall_mm_24h": 190.0}
    payload.update(overrides)
    return client.post("/api/assess", json=payload)


def test_assess_returns_rule_estimate_and_ml_prototype(client, online_weather):
    response = _assess(client)
    assert response.status_code == 200
    body = response.json()

    rule = body["rule_estimate"]
    assert rule["kind"] == "Demo Risk Estimate"
    assert rule["is_trained_model"] is False
    assert rule["engine_mode"] == "rule-based-demo"
    assert 0 <= rule["score"] <= 100
    assert rule["risk_level"] in ("Low", "Moderate", "High", "Severe")
    assert rule["explanation"]


def test_factors_sum_to_score_and_carry_explanations(client, online_weather):
    body = _assess(client).json()
    factors = body["rule_estimate"]["factors"]
    assert len(factors) == 7
    assert abs(sum(f["points"] for f in factors) - body["rule_estimate"]["score"]) < 0.15

    for factor in factors:
        assert factor["bucket"] in ("weather", "illustrative")
        assert factor["note"]
        assert factor["weight_max"] > 0
        assert 0 <= factor["points"] <= factor["weight_max"] + 0.01


def test_weather_inputs_are_separated_from_illustrative_inputs(client, online_weather):
    body = _assess(client).json()
    assert set(body["inputs"]) == {"weather_derived", "illustrative_zone_attributes"}
    assert body["inputs"]["weather_derived"]["source"] == "manual"
    assert body["inputs"]["illustrative_zone_attributes"]["attributes_illustrative"] is True


def test_assessment_is_deterministic(client, online_weather):
    first = _assess(client).json()["rule_estimate"]
    second = _assess(client).json()["rule_estimate"]

    # assessment_id and timestamps differ; the actual risk maths must not.
    first.pop("explanation")
    second.pop("explanation")
    assert first == second
    assert _assess(client).json()["rule_estimate"]["explanation"] == \
        _assess(client).json()["rule_estimate"]["explanation"]


def test_higher_rainfall_never_lowers_the_score(client, online_weather):
    low = _assess(client, rainfall_mm_1h=5.0, rainfall_mm_24h=10.0).json()["rule_estimate"]["score"]
    high = _assess(client, rainfall_mm_1h=80.0, rainfall_mm_24h=260.0).json()["rule_estimate"]["score"]
    assert high > low


def test_unknown_zone_returns_404_with_helpful_message(client, online_weather):
    response = _assess(client, zone_id="atlantis")
    assert response.status_code == 404
    assert "atlantis" in response.json()["detail"]
    assert "velachery" in response.json()["detail"]


def test_missing_location_returns_422(client, online_weather):
    response = client.post("/api/assess", json={"rainfall_mm_1h": 10.0})
    assert response.status_code == 422
    assert "latitude" in response.json()["detail"]


def test_out_of_range_rainfall_returns_422(client, online_weather):
    response = _assess(client, rainfall_mm_1h=500.0)
    assert response.status_code == 422
    assert response.json()["detail"] == "Request validation failed."


def test_unknown_field_is_rejected(client, online_weather):
    response = _assess(client, bogus_field="nope")
    assert response.status_code == 422


def test_coordinates_snap_to_nearest_catalogue_zone(client, online_weather):
    response = client.post(
        "/api/assess",
        json={"latitude": 12.9805, "longitude": 80.2230, "rainfall_mm_1h": 20.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["zone"]["id"] == "velachery"
    assert "nearest" in body["data_quality"]["resolved_zone"]


def test_distant_coordinates_use_user_supplied_point(client, online_weather):
    response = client.post(
        "/api/assess",
        json={"latitude": 19.0760, "longitude": 72.8777, "rainfall_mm_1h": 20.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["zone"]["id"] == "custom"
    assert body["data_quality"]["resolved_zone"] == "user-supplied coordinates"


def test_ml_prototype_is_never_marked_reliable(client, online_weather):
    body = _assess(client).json()
    prototype = body["ml_prototype"]
    assert prototype["reliable"] is False
    assert prototype["is_trained_model"] is True
    assert "synthetic" in prototype["badge"].lower() or "synthetic" in prototype["caveat"].lower()
    if prototype["available"]:
        assert 0.0 <= prototype["probability_flood"] <= 1.0
        assert prototype["imputed_columns"], "expected imputed columns to be disclosed"


def test_disclaimer_present(client, online_weather):
    body = _assess(client).json()
    assert "not an official flood-warning system" in body["disclaimer"].lower()
    assert "illustrative" in body["risk_scale_note"].lower()

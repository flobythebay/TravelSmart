from app.trip_interpreter import fallback_interpretation

def test_extracts_trip_length_airline_and_departure():
    result = fallback_interpretation("Visit Tokyo for 8 days in March, prefer Delta and evening flights")
    assert result.trip_length_days == 8
    assert "Delta" in result.preferred_airlines
    assert result.preferred_departure_period == "evening"
    assert result.extraction_method == "fallback"

def test_does_not_invent_live_prices():
    result = fallback_interpretation("A trip to Paris next spring")
    assert result.budget_total is None
    assert result.earliest_departure is None
    assert result.latest_departure is None

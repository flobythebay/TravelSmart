from app.trip_interpreter import fallback_interpretation


def test_extracts_destination_duration_and_airline_preferences():
    result = fallback_interpretation("Visit Tokyo for 8 days in March. I prefer Delta and evening flights.")
    assert result.destination == "Tokyo"
    assert result.trip_length_days == 8
    assert result.preferred_airlines == ["Delta"]
    assert result.preferred_departure_period == "evening"
    assert result.date_flexibility == "approximate"
    assert result.earliest_departure is None


def test_broad_month_does_not_invent_year_or_exact_dates():
    result = fallback_interpretation("A trip to Paris sometime in March for about a week")
    assert result.travel_window_label == "march"
    assert result.earliest_departure is None
    assert result.latest_departure is None
    assert any("year" in question.lower() for question in result.clarification_questions)


def test_explicit_iso_date_is_preserved():
    result = fallback_interpretation("Fly to Tokyo on 2027-03-12")
    assert result.earliest_departure == "2027-03-12"
    assert result.latest_departure == "2027-03-12"
    assert result.date_flexibility == "exact"


def test_budget_scope_is_not_assumed():
    result = fallback_interpretation("Visit Rome for 6 days with a budget of $1800")
    assert result.budget_total == 1800
    assert result.budget_scope == "unspecified"
    assert any("whole trip or per person" in question for question in result.clarification_questions)


def test_explicit_total_budget_and_nonstop_constraint():
    result = fallback_interpretation("I need nonstop flights and a total budget of $2500 to visit Seoul")
    assert result.max_stops == 0
    assert "Nonstop flights" in result.hard_constraints
    assert result.budget_total == 2500
    assert result.budget_scope == "total"


def test_soft_airline_preference_does_not_exclude_other_carriers():
    result = fallback_interpretation("Visit Miami, preferably on Alaska Airlines")
    assert result.preferred_airlines == ["Alaska Airlines"]
    assert result.excluded_airlines == []
    assert result.soft_preferences


def test_origin_and_hotel_transit_preference():
    result = fallback_interpretation("Fly from Seattle to New York for 5 nights, hotel near the subway")
    assert result.origin == "Seattle"
    assert result.destination == "New York"
    assert result.trip_length_nights == 5
    assert result.trip_length_days == 6
    assert result.hotel_near_transit is True


def test_unknown_values_remain_unknown():
    result = fallback_interpretation("I want to go somewhere warm for a few days")
    assert result.destination is None
    assert result.budget_total is None
    assert result.earliest_departure is None
    assert result.clarification_questions

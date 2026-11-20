from typing import Literal

from pydantic import BaseModel, Field, field_validator


class InterpretTripRequest(BaseModel):
    request: str = Field(min_length=5, max_length=4000)


class TripIntent(BaseModel):
    """Normalized trip requirements. Null means unknown, not a guessed value."""

    origin: str | None = None
    destination: str | None = None
    destination_strategy: Literal["fixed", "same_country_airports"] = "same_country_airports"

    # Date windows are only populated when the dates can be identified safely.
    earliest_departure: str | None = None
    latest_departure: str | None = None
    travel_window_label: str | None = None
    date_flexibility: Literal["exact", "flexible", "approximate", "unspecified"] = "unspecified"

    trip_length_days: int | None = Field(default=None, ge=1, le=90)
    trip_length_nights: int | None = Field(default=None, ge=0, le=89)

    budget_total: float | None = Field(default=None, gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    budget_scope: Literal["total", "per_person", "per_night", "unspecified"] = "unspecified"

    preferred_airlines: list[str] = Field(default_factory=list)
    excluded_airlines: list[str] = Field(default_factory=list)
    avoid_layovers: bool = False
    max_stops: int | None = Field(default=None, ge=0, le=3)
    preferred_departure_period: Literal["morning", "afternoon", "evening", "overnight"] | None = None
    preferred_arrival_period: Literal["morning", "afternoon", "evening", "overnight"] | None = None

    preferred_hotel_chains: list[str] = Field(default_factory=list)
    hotel_near_transit: bool = False
    hotel_location: str | None = None

    # Keep the original fields for compatibility with the first frontend.
    must_haves: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    extraction_method: Literal["ai", "fallback"] = "fallback"

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

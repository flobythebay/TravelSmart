from typing import Literal
from pydantic import BaseModel, Field

class InterpretTripRequest(BaseModel):
    request: str = Field(min_length=5, max_length=4000)

class TripIntent(BaseModel):
    destination: str | None = None
    earliest_departure: str | None = None
    latest_departure: str | None = None
    trip_length_days: int | None = Field(default=None, ge=1, le=90)
    budget_total: float | None = Field(default=None, gt=0)
    currency: str = "USD"
    preferred_airlines: list[str] = Field(default_factory=list)
    avoid_layovers: bool = False
    preferred_departure_period: Literal["morning", "afternoon", "evening", "overnight"] | None = None
    must_haves: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    extraction_method: Literal["ai", "fallback"] = "fallback"

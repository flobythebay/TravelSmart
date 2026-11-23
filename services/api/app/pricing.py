"""Deterministic exploration and ranking of provider-sourced trip quotes.

This module never fetches or invents prices. Provider adapters normalize quotes into
these models; the planner explores the supplied date, duration, and airport choices.
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FlightQuote(BaseModel):
    departure_date: date
    return_date: date
    origin_airport: str = Field(min_length=3, max_length=4)
    arrival_airport: str = Field(min_length=3, max_length=4)
    return_departure_airport: str = Field(min_length=3, max_length=4)
    arrival_country: str = Field(min_length=2, max_length=80)
    return_departure_country: str = Field(min_length=2, max_length=80)
    price: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    stops: int = Field(default=0, ge=0, le=4)
    booking_url: str | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.return_date <= self.departure_date:
            raise ValueError("Flight return date must be after departure date")
        return self


class HotelQuote(BaseModel):
    check_in: date
    check_out: date
    name: str = Field(min_length=1, max_length=160)
    price: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    booking_url: str | None = None

    @model_validator(mode="after")
    def validate_stay(self):
        if self.check_out <= self.check_in:
            raise ValueError("Hotel check-out must be after check-in")
        return self


class TripPriceSearchRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=120)
    destination_country: str = Field(min_length=2, max_length=80)
    origin_airport: str = Field(min_length=3, max_length=4)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    earliest_departure: date | None = None
    latest_departure: date | None = None
    min_nights: int | None = Field(default=None, ge=1, le=89)
    max_nights: int | None = Field(default=None, ge=1, le=89)
    allow_same_country_airports: bool = True
    preferred_destination_airport: str | None = Field(default=None, min_length=3, max_length=4)
    max_stops: int | None = Field(default=None, ge=0, le=4)
    flight_quotes: list[FlightQuote] = Field(min_length=1, max_length=500)
    hotel_quotes: list[HotelQuote] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_search_window(self):
        if self.earliest_departure and self.latest_departure:
            if self.latest_departure < self.earliest_departure:
                raise ValueError("Latest departure must be on or after earliest departure")
        if self.min_nights and self.max_nights and self.max_nights < self.min_nights:
            raise ValueError("Maximum nights must be greater than or equal to minimum nights")
        if not self.allow_same_country_airports and not self.preferred_destination_airport:
            raise ValueError("A preferred destination airport is required when airport flexibility is disabled")
        return self


class TripPriceRecommendation(BaseModel):
    destination: str
    departure_date: date
    return_date: date
    origin_airport: str
    arrival_airport: str
    return_departure_airport: str
    flight_price: float
    hotel_name: str
    hotel_price: float
    total_price: float
    currency: str
    nights: int
    booking_links: dict[str, str] = Field(default_factory=dict)
    rationale: str


class TripPriceSearchResponse(BaseModel):
    recommendations: list[TripPriceRecommendation]
    rejected_options: int
    explored_departure_dates: int
    explored_airport_pairs: int
    explored_trip_lengths: list[int]
    price_data_note: str


def recommend_trip_options(request: TripPriceSearchRequest) -> TripPriceSearchResponse:
    """Explore supplied quote combinations and rank by total flight + hotel cost.

    The destination remains fixed. When airport flexibility is enabled, both the
    arrival and return-departure airports must be in the requested country.
    """
    currency = request.currency.upper()
    recommendations: list[TripPriceRecommendation] = []
    rejected = 0

    for flight in request.flight_quotes:
        nights = (flight.return_date - flight.departure_date).days
        if flight.origin_airport.upper() != request.origin_airport.upper():
            rejected += 1
            continue
        if request.earliest_departure and flight.departure_date < request.earliest_departure:
            rejected += 1
            continue
        if request.latest_departure and flight.departure_date > request.latest_departure:
            rejected += 1
            continue
        if request.min_nights is not None and nights < request.min_nights:
            rejected += 1
            continue
        if request.max_nights is not None and nights > request.max_nights:
            rejected += 1
            continue

        same_country = (
            flight.arrival_country.casefold() == request.destination_country.casefold()
            and flight.return_departure_country.casefold() == request.destination_country.casefold()
        )
        if not same_country:
            rejected += 1
            continue
        if not request.allow_same_country_airports:
            if flight.arrival_airport.upper() != request.preferred_destination_airport.upper():
                rejected += 1
                continue
        if request.max_stops is not None and flight.stops > request.max_stops:
            rejected += 1
            continue
        if flight.currency.upper() != currency:
            rejected += 1
            continue

        matching_hotels = [
            hotel for hotel in request.hotel_quotes
            if hotel.check_in == flight.departure_date
            and hotel.check_out == flight.return_date
            and hotel.currency.upper() == currency
        ]
        for hotel in matching_hotels:
            links = {}
            if flight.booking_url:
                links["flight"] = flight.booking_url
            if hotel.booking_url:
                links["hotel"] = hotel.booking_url
            recommendations.append(TripPriceRecommendation(
                destination=request.destination,
                departure_date=flight.departure_date,
                return_date=flight.return_date,
                origin_airport=flight.origin_airport.upper(),
                arrival_airport=flight.arrival_airport.upper(),
                return_departure_airport=flight.return_departure_airport.upper(),
                flight_price=flight.price,
                hotel_name=hotel.name,
                hotel_price=hotel.price,
                total_price=round(flight.price + hotel.price, 2),
                currency=currency,
                nights=(hotel.check_out - hotel.check_in).days,
                booking_links=links,
                rationale="Ranked by combined flight and hotel price; destination country preserved.",
            ))

    recommendations.sort(key=lambda item: (item.total_price, item.departure_date, item.arrival_airport))
    return TripPriceSearchResponse(
        recommendations=recommendations[:20],
        rejected_options=rejected,
        explored_departure_dates=len({item.departure_date for item in recommendations}),
        explored_airport_pairs=len({
            (item.arrival_airport, item.return_departure_airport) for item in recommendations
        }),
        explored_trip_lengths=sorted({item.nights for item in recommendations}),
        price_data_note=(
            "Recommendations use only the quotes supplied to this endpoint; prices and "
            "availability are not independently verified."
        ),
    )

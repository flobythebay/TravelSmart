"""Deterministic ranking of provider-sourced flight and hotel options.

This module deliberately does not fetch or invent prices. A future provider adapter
can normalize live quotes into these models before calling recommend_trip_options.
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
    allow_same_country_airports: bool = True
    max_stops: int | None = Field(default=None, ge=0, le=4)
    flight_quotes: list[FlightQuote] = Field(min_length=1, max_length=500)
    hotel_quotes: list[HotelQuote] = Field(min_length=1, max_length=500)


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
    price_data_note: str


def recommend_trip_options(request: TripPriceSearchRequest) -> TripPriceSearchResponse:
    """Rank matching flight+hotel combinations by combined cash price.

    Destination stays fixed. Alternative arrival/departure airports are accepted
    only when both are in the requested destination country.
    """
    currency = request.currency.upper()
    recommendations: list[TripPriceRecommendation] = []
    rejected = 0

    for flight in request.flight_quotes:
        if flight.origin_airport.upper() != request.origin_airport.upper():
            rejected += 1
            continue
        same_country = (
            flight.arrival_country.casefold() == request.destination_country.casefold()
            and flight.return_departure_country.casefold() == request.destination_country.casefold()
        )
        if not same_country:
            rejected += 1
            continue
        if not request.allow_same_country_airports and (
            flight.arrival_airport.upper() != request.origin_airport.upper()
        ):
            # Strict airport matching is intentionally conservative until a
            # destination's preferred airport is explicitly supplied.
            rejected += 1
            continue
        if request.max_stops is not None and flight.stops > request.max_stops:
            rejected += 1
            continue
        if flight.currency.upper() != currency:
            rejected += 1
            continue

        for hotel in request.hotel_quotes:
            if hotel.check_in != flight.departure_date or hotel.check_out != flight.return_date:
                continue
            if hotel.currency.upper() != currency:
                rejected += 1
                continue
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
        price_data_note="Recommendations use only the quotes supplied to this endpoint; prices and availability are not independently verified.",
    )

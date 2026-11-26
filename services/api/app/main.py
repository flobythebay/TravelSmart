import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import InterpretTripRequest, TripIntent
from app.trip_interpreter import interpret_trip
from app.pricing import TripPriceSearchRequest, TripPriceSearchResponse, recommend_trip_options
from app.flight_provider import FlightProviderError, search_google_flights

app = FastAPI(title="TravelSmart API", version="0.1.0", description="AI-assisted flexible travel planning API.")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS","http://localhost:3000").split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health() -> dict[str, str]:
    return {"status":"ok","service":"travelsmart-api"}

@app.post("/api/v1/trips/interpret", response_model=TripIntent)
def interpret_trip_request(payload: InterpretTripRequest) -> TripIntent:
    return interpret_trip(payload.request)


@app.post("/api/v1/trips/recommendations", response_model=TripPriceSearchResponse)
def recommend_trip_prices(payload: TripPriceSearchRequest) -> TripPriceSearchResponse:
    """Explore supplied date, duration, and same-country airport quotes by total cost."""
    return recommend_trip_options(payload)


@app.get("/api/v1/flights/search")
def search_flights(
    departure_id: str = Query(min_length=3, max_length=80),
    arrival_id: str = Query(min_length=3, max_length=80),
    outbound_date: str = Query(pattern=r"^\\d{4}-\\d{2}-\\d{2}$"),
    return_date: str | None = Query(default=None, pattern=r"^\\d{4}-\\d{2}-\\d{2}$"),
    currency: str = Query(default="USD", min_length=3, max_length=3),
    adults: int = Query(default=1, ge=1, le=9),
    max_stops: int | None = Query(default=None, ge=0, le=2),
) -> dict:
    """Search Google Flights through SerpApi; results are provider-sourced and may change."""
    try:
        return search_google_flights(
            departure_id=departure_id,
            arrival_id=arrival_id,
            outbound_date=outbound_date,
            return_date=return_date,
            currency=currency,
            adults=adults,
            stops=None if max_stops is None else max_stops + 1,
        )
    except FlightProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

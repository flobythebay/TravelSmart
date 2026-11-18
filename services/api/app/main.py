import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import InterpretTripRequest, TripIntent
from app.trip_interpreter import interpret_trip

app = FastAPI(title="TravelSmart API", version="0.1.0", description="AI-assisted flexible travel planning API.")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS","http://localhost:3000").split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health() -> dict[str, str]:
    return {"status":"ok","service":"travelsmart-api"}

@app.post("/api/v1/trips/interpret", response_model=TripIntent)
def interpret_trip_request(payload: InterpretTripRequest) -> TripIntent:
    return interpret_trip(payload.request)

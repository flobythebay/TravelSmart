"""SerpApi Google Flights adapter. Credentials remain server-side."""
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SERPAPI_ENDPOINT = "https://serpapi.com/search"


class FlightProviderError(RuntimeError):
    """Raised when SerpApi cannot return a usable flight search."""


def search_google_flights(
    *,
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str | None = None,
    currency: str = "USD",
    adults: int = 1,
    stops: int | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Return provider results without inventing prices or booking links."""
    key = api_key or os.getenv("SERPAPI_API_KEY")
    if not key:
        raise FlightProviderError("Flight search is not configured: SERPAPI_API_KEY is missing.")

    params: dict[str, str] = {
        "engine": "google_flights",
        "api_key": key,
        "departure_id": departure_id.upper(),
        "arrival_id": arrival_id.upper(),
        "outbound_date": outbound_date,
        "currency": currency.upper(),
        "adults": str(adults),
        "type": "1" if return_date else "2",
    }
    if return_date:
        params["return_date"] = return_date
    if stops is not None:
        params["stops"] = str(stops)

    request = Request(f"{SERPAPI_ENDPOINT}?{urlencode(params)}", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            import json
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise FlightProviderError(f"Flight provider returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise FlightProviderError("Could not retrieve flight results from the provider.") from exc

    if payload.get("error"):
        raise FlightProviderError(str(payload["error"]))
    return payload

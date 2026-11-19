import json
import os
import re
from datetime import date

from openai import OpenAI

from app.schemas import TripIntent

SYSTEM_PROMPT = """Extract travel intent into the supplied JSON schema. Only return facts supported
by the user's request. Never invent dates, prices, schedules, hotel inventory, award availability,
or loyalty balances. Keep broad periods such as 'in March' as labels; do not invent a year or exact
dates. Separate hard constraints (must, need, required, only) from soft preferences (prefer,
ideally, if possible). A preferred airline does not exclude other airlines. Do not assume a budget
is per-person or total unless stated. Ask concise clarification questions for missing details."""


AIRLINES = {
    "delta": "Delta", "united": "United", "alaska": "Alaska Airlines",
    "alaska airlines": "Alaska Airlines", "american": "American Airlines",
    "american airlines": "American Airlines", "southwest": "Southwest",
    "jetblue": "JetBlue", "spirit": "Spirit", "frontier": "Frontier",
    "hawaiian": "Hawaiian Airlines", "air canada": "Air Canada",
    "british airways": "British Airways", "lufthansa": "Lufthansa",
    "emirates": "Emirates", "qatar airways": "Qatar Airways",
}
MONTHS = "january february march april may june july august september october november december".split()
SEASONS = "spring summer fall autumn winter".split()


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _extract_period(text: str) -> tuple[str | None, str | None, str | None]:
    """Return exact ISO boundaries only when the user explicitly supplied a year."""
    iso_range = re.search(r"\b(20\d{2}-\d{2}-\d{2})\s+(?:to|through|-)\s+(20\d{2}-\d{2}-\d{2})\b", text)
    if iso_range:
        try:
            first = date.fromisoformat(iso_range.group(1))
            last = date.fromisoformat(iso_range.group(2))
            return first.isoformat(), last.isoformat(), f"{first.isoformat()} to {last.isoformat()}"
        except ValueError:
            pass

    iso = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", text)
    if iso:
        try:
            parsed = date.fromisoformat(iso.group(0))
            return parsed.isoformat(), parsed.isoformat(), parsed.isoformat()
        except ValueError:
            pass

    month_names = "|".join(MONTHS)
    full_date = re.search(rf"\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+(20\d{{2}})\b", text, re.I)
    if full_date:
        try:
            parsed = date(int(full_date.group(3)), MONTHS.index(full_date.group(1).lower()) + 1, int(full_date.group(2)))
            return parsed.isoformat(), parsed.isoformat(), parsed.isoformat()
        except ValueError:
            pass

    month_year = re.search(rf"\b({month_names})\s+(20\d{{2}})\b", text, re.I)
    if month_year:
        return None, None, f"{month_year.group(1).title()} {month_year.group(2)}"

    range_with_year = re.search(rf"\b(?:between|from)\s+({month_names})\s+(\d{{1,2}})\s+(?:and|to|through)\s+({month_names})\s+(\d{{1,2}})[,]?\s+(20\d{{2}})\b", text, re.I)
    if range_with_year:
        try:
            year = int(range_with_year.group(5))
            first = date(year, MONTHS.index(range_with_year.group(1).lower()) + 1, int(range_with_year.group(2)))
            last = date(year, MONTHS.index(range_with_year.group(3).lower()) + 1, int(range_with_year.group(4)))
            return first.isoformat(), last.isoformat(), f"{first.isoformat()} to {last.isoformat()}"
        except ValueError:
            pass

    broad = re.search(rf"\b(?:in|during|sometime in|around|this|next)\s+({month_names}|{'|'.join(SEASONS)})\b", text, re.I)
    if broad:
        return None, None, broad.group(1).lower()

    date_range = re.search(r"\b(?:between|from)\s+([A-Za-z]+\s+\d{1,2})\s+(?:and|to|through)\s+([A-Za-z]+\s+\d{1,2})\b", text, re.I)
    if date_range:
        return None, None, f"{date_range.group(1)} to {date_range.group(2)}"
    return None, None, None

def fallback_interpretation(request: str) -> TripIntent:
    text = request.strip()
    lower = text.lower()
    hard: list[str] = []
    soft: list[str] = []
    notes: list[str] = []

    destination_match = re.search(r"\b(?:to|visit)\s+([A-Z][A-Za-zÀ-ÿ' -]{1,35}?)(?=\s+(?:for|in|during|between|around|next|this|with|and|,|\.)|[,.]|$)", text)
    destination = destination_match.group(1).strip() if destination_match else None
    origin_match = re.search(r"\bfrom\s+([A-Z][A-Za-zÀ-ÿ' -]{1,35}?)(?=\s+(?:to|for|in|during|between|around|on|,)|[,.]|$)", text)
    origin = origin_match.group(1).strip() if origin_match else None

    duration = re.search(r"\b(\d{1,2})\s*(day|days|night|nights)\b", lower)
    days = int(duration.group(1)) if duration and "day" in duration.group(2) else None
    nights = int(duration.group(1)) if duration and "night" in duration.group(2) else None
    if days is None and nights is not None:
        days = nights + 1

    preferred_airlines = [name for alias, name in AIRLINES.items() if re.search(rf"\b{re.escape(alias)}\b", lower)]
    excluded_airlines = []
    for alias, name in AIRLINES.items():
        if re.search(rf"\b(?:not|no|avoid|exclude)\s+(?:flying\s+)?{re.escape(alias)}\b", lower):
            excluded_airlines.append(name)
    preferred_airlines = [name for name in _unique(preferred_airlines) if name not in excluded_airlines]

    budget_match = re.search(r"(?:\$|\b(?:budget|under|below)\s*\$?)(\d[\d,]*(?:\.\d{1,2})?)", text, re.I)
    budget = float(budget_match.group(1).replace(",", "")) if budget_match else None
    currency = "EUR" if "€" in text or re.search(r"\bEUR\b", text, re.I) else "GBP" if "£" in text or re.search(r"\bGBP\b", text, re.I) else "CAD" if re.search(r"\bCAD\b", text, re.I) else "USD"
    budget_scope = "unspecified"
    if budget is not None:
        if re.search(r"\bper person\b|\beach\b", lower): budget_scope = "per_person"
        elif re.search(r"\bper night\b", lower): budget_scope = "per_night"
        elif re.search(r"\btotal\b|\ball[- ]in\b|\bwhole trip\b|\bentire trip\b", lower): budget_scope = "total"

    departure = next((period for period in ["morning", "afternoon", "evening", "overnight"] if re.search(rf"\b{period}\b", lower)), None)
    arrival_match = re.search(r"\barriv(?:e|al)\s+(?:in the\s+)?(morning|afternoon|evening|overnight)\b", lower)
    arrival = arrival_match.group(1) if arrival_match else None

    nonstop_mentioned = bool(re.search(r"\b(non[- ]?stop|no layovers?|direct flights?)\b", lower))
    max_stops_match = re.search(r"\b(?:up to|at most)\s+(\d)\s+stops?\b", lower)
    max_stops = 0 if nonstop_mentioned else int(max_stops_match.group(1)) if max_stops_match else None

    # Determine constraint strength per phrase, not from unrelated words elsewhere in the request.
    hard_nonstop = bool(re.search(r"\b(?:must|need|required|require|only)\b.{0,45}\b(?:non[- ]?stop|direct flights?|no layovers?)\b|\b(?:non[- ]?stop|direct flights?)\b.{0,25}\b(?:only|required|must)\b", lower))
    if hard_nonstop:
        hard.append("Nonstop flights")
    elif nonstop_mentioned:
        soft.append("Prefer nonstop flights")

    if departure:
        if re.search(rf"\b(?:must|need|required|only)\b.{{0,35}}\b{departure}\b", lower):
            hard.append(f"{departure.capitalize()} departures")
        else:
            soft.append(f"Prefer {departure} departures")
    if arrival:
        soft.append(f"Prefer {arrival} arrivals")
    if preferred_airlines:
        soft.append("Prefer " + ", ".join(preferred_airlines))
    if excluded_airlines:
        hard.append("Exclude " + ", ".join(_unique(excluded_airlines)))
    if max_stops_match:
        hard.append(f"At most {max_stops} stops")

    hotel_near_transit = bool(re.search(r"\b(?:near|close to|walking distance of)\s+(?:public )?transit|near (?:the )?(?:subway|metro|train station|light rail)\b", lower))
    if hotel_near_transit:
        transit_hard = bool(re.search(r"\b(?:must|need|required|only)\b.{0,55}\b(?:near transit|near public transportation|near the subway|near a train)\b", lower))
        (hard if transit_hard else soft).append("Hotel near public transportation")

    hotel_names = ["Marriott", "Hilton", "Hyatt", "IHG", "InterContinental", "Holiday Inn", "Westin", "Sheraton"]
    hotel_chains = [name for name in hotel_names if name.lower() in lower]

    start, end, label = _extract_period(text)
    flexibility = "exact" if start and end == start else "flexible" if start and end else "approximate" if label and label.lower() in MONTHS + SEASONS else "flexible" if label else "unspecified"
    if label and start is None:
        notes.append(f"Travel period stated as '{label}'. No year or exact dates were inferred.")

    clarification = []
    if destination is None:
        clarification.append("Where would you like to travel?")
    if label and start is None and not re.search(r"20\\d{2}", label):
        clarification.append("What year do you mean for that travel window?")
    if budget is not None and budget_scope == "unspecified":
        clarification.append("Is that budget for the whole trip or per person?")

    if "points" in lower or "miles" in lower or "rewards" in lower:
        notes.append("Travel rewards mentioned; collect program and balance details in a later step.")

    return TripIntent(
        origin=origin, destination=destination,
        earliest_departure=start, latest_departure=end,
        travel_window_label=label, date_flexibility=flexibility,
        trip_length_days=days, trip_length_nights=nights,
        budget_total=budget, currency=currency, budget_scope=budget_scope,
        preferred_airlines=_unique(preferred_airlines), excluded_airlines=_unique(excluded_airlines),
        avoid_layovers=hard_nonstop, max_stops=max_stops,
        preferred_departure_period=departure, preferred_arrival_period=arrival,
        preferred_hotel_chains=_unique(hotel_chains), hotel_near_transit=hotel_near_transit,
        must_haves=_unique(hard), nice_to_haves=_unique(soft),
        hard_constraints=_unique(hard), soft_preferences=_unique(soft),
        clarification_questions=_unique(clarification), notes=notes,
        extraction_method="fallback",
    )


def _ai_schema() -> dict:
    nullable_string = {"type": ["string", "null"]}
    return {
        "type": "object",
        "properties": {
            "origin": nullable_string, "destination": nullable_string,
            "earliest_departure": nullable_string, "latest_departure": nullable_string,
            "travel_window_label": nullable_string,
            "date_flexibility": {"type":"string","enum":["exact","flexible","approximate","unspecified"]},
            "trip_length_days": {"type":["integer","null"]},
            "trip_length_nights": {"type":["integer","null"]},
            "budget_total": {"type":["number","null"]}, "currency":{"type":"string"},
            "budget_scope":{"type":"string","enum":["total","per_person","per_night","unspecified"]},
            "preferred_airlines":{"type":"array","items":{"type":"string"}},
            "excluded_airlines":{"type":"array","items":{"type":"string"}},
            "avoid_layovers":{"type":"boolean"}, "max_stops":{"type":["integer","null"]},
            "preferred_departure_period":{"type":["string","null"],"enum":["morning","afternoon","evening","overnight",None]},
            "preferred_arrival_period":{"type":["string","null"],"enum":["morning","afternoon","evening","overnight",None]},
            "preferred_hotel_chains":{"type":"array","items":{"type":"string"}},
            "hotel_near_transit":{"type":"boolean"}, "hotel_location":nullable_string,
            "must_haves":{"type":"array","items":{"type":"string"}},
            "nice_to_haves":{"type":"array","items":{"type":"string"}},
            "hard_constraints":{"type":"array","items":{"type":"string"}},
            "soft_preferences":{"type":"array","items":{"type":"string"}},
            "clarification_questions":{"type":"array","items":{"type":"string"}},
            "notes":{"type":"array","items":{"type":"string"}},
        },
        "required":["origin","destination","earliest_departure","latest_departure","travel_window_label","date_flexibility","trip_length_days","trip_length_nights","budget_total","currency","budget_scope","preferred_airlines","excluded_airlines","avoid_layovers","max_stops","preferred_departure_period","preferred_arrival_period","preferred_hotel_chains","hotel_near_transit","hotel_location","must_haves","nice_to_haves","hard_constraints","soft_preferences","clarification_questions","notes"],
        "additionalProperties":False,
    }


def interpret_trip(request: str) -> TripIntent:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_interpretation(request)
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":request}],
            response_format={"type":"json_schema","json_schema":{"name":"trip_intent","strict":True,"schema":_ai_schema()}},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        data["extraction_method"] = "ai"
        data["must_haves"] = data.get("must_haves") or data.get("hard_constraints", [])
        data["nice_to_haves"] = data.get("nice_to_haves") or data.get("soft_preferences", [])
        return TripIntent.model_validate(data)
    except Exception:
        return fallback_interpretation(request)

import json
import os
import re
from openai import OpenAI
from app.schemas import TripIntent

SYSTEM_PROMPT = """Extract explicit travel intent into the supplied JSON schema. Never invent dates,
prices, availability, balances, or destinations. Separate hard requirements from soft preferences.
Use ISO dates only when unambiguous; preserve broad months/seasons in notes. Extract airline names.
Only set avoid_layovers when the user clearly requires nonstop travel. Default currency is USD."""

def fallback_interpretation(request: str) -> TripIntent:
    text = request.strip()
    lower = text.lower()
    destination = None
    match = re.search(r"\b(?:to|in|visit)\s+([A-Z][A-Za-zÀ-ÿ -]{1,35}?)(?=\s+(?:for|in|during|between|around|next|this|with|and|,|\.)|[,.]|$)", text)
    if match:
        destination = match.group(1).strip()
    length_match = re.search(r"\b(\d{1,2})\s*(?:-|to)?\s*(?:day|days|night|nights)\b", lower)
    length = int(length_match.group(1)) if length_match else None
    airlines = [a for a in ["Delta", "United", "Alaska Airlines", "American Airlines", "Southwest", "JetBlue"] if a.lower() in lower]
    departure = next((p for p in ["morning", "afternoon", "evening", "overnight"] if p in lower), None)
    budget_match = re.search(r"(?:\$|\b(?:budget|under|below)\s*\$?)(\d[\d,]*)", text, re.I)
    budget = float(budget_match.group(1).replace(",", "")) if budget_match else None
    nonstop = any(term in lower for term in ["nonstop", "non-stop", "no layover", "no stop", "direct flight"])
    notes = []
    for month in ["january","february","march","april","may","june","july","august","september","october","november","december","spring","summer","fall","autumn","winter"]:
        if month in lower:
            notes.append(f"Approximate travel period mentioned: {month}")
            break
    prefs = []
    if departure: prefs.append(f"Prefer {departure} departures")
    if "hotel" in lower and ("near transit" in lower or "near public transportation" in lower):
        prefs.append("Hotel near public transportation")
    if "points" in lower or "miles" in lower or "rewards" in lower:
        notes.append("Travel rewards mentioned; collect program and balance details in a later step")
    return TripIntent(destination=destination, trip_length_days=length, budget_total=budget,
        preferred_airlines=airlines, avoid_layovers=nonstop, preferred_departure_period=departure,
        nice_to_haves=prefs, notes=notes, extraction_method="fallback")

def interpret_trip(request: str) -> TripIntent:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return fallback_interpretation(request)
    schema = {
      "type":"object",
      "properties":{
        "destination":{"type":["string","null"]},
        "earliest_departure":{"type":["string","null"]},
        "latest_departure":{"type":["string","null"]},
        "trip_length_days":{"type":["integer","null"]},
        "budget_total":{"type":["number","null"]},
        "currency":{"type":"string"},
        "preferred_airlines":{"type":"array","items":{"type":"string"}},
        "avoid_layovers":{"type":"boolean"},
        "preferred_departure_period":{"type":["string","null"],"enum":["morning","afternoon","evening","overnight",None]},
        "must_haves":{"type":"array","items":{"type":"string"}},
        "nice_to_haves":{"type":"array","items":{"type":"string"}},
        "notes":{"type":"array","items":{"type":"string"}}
      },
      "required":["destination","earliest_departure","latest_departure","trip_length_days","budget_total","currency","preferred_airlines","avoid_layovers","preferred_departure_period","must_haves","nice_to_haves","notes"],
      "additionalProperties":False
    }
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL","gpt-4.1-mini"),
            messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":request}],
            response_format={"type":"json_schema","json_schema":{"name":"trip_intent","strict":True,"schema":schema}}
        )
        data = json.loads(response.choices[0].message.content or "{}")
        data["extraction_method"] = "ai"
        return TripIntent.model_validate(data)
    except Exception:
        return fallback_interpretation(request)

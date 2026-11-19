# TravelSmart ✈️

**AI-powered travel planning that finds the best way to take the trip you want.**

TravelSmart turns flexible travel ideas into ranked trip options by combining flight schedules, hotel prices, traveler preferences, and (eventually) loyalty points and miles.

## Product vision

A traveler can describe a trip in natural language, including approximate dates and trip length. TravelSmart should:
1. Use AI to turn natural-language requests into structured trip preferences.
2. Search multiple date combinations for flights and hotels.
3. Optimize the **combined trip cost**, not just the cheapest flight.
4. Respect hard requirements and rank softer preferences (airline, departure time, stops, hotel location).
5. Explain trade-offs using verified provider results.
6. Grow into rewards optimization: compare cash fares with award availability, points, transfer ratios, taxes, and fees.

## Engineering principles

- **AI for understanding and explanations; code for truth.** LLMs extract intent and explain verified results. Deterministic services calculate totals, enforce constraints, and rank options.
- Never invent prices, schedules, award availability, transfer ratios, or hotel inventory.
- Distinguish hard constraints from flexible preferences.
- Show total cash cost and points used separately; do not treat points as cash.
- Keep secrets server-side. Never collect full payment-card numbers or account passwords.
- Start as a modular backend with a background worker, not a fleet of microservices.

## Initial stack

| Area | Technology |
|---|---|
| Web | Next.js, React, TypeScript |
| API / AI orchestration | Python, FastAPI, Pydantic |
| LLM integration | OpenAI API (optional via environment variable) |
| Data | PostgreSQL (infrastructure scaffolded; persistence not wired yet) |
| Cache / jobs | Redis, Celery (planned) |
| Local development | Docker Compose |
| CI | GitHub Actions |

## Repository layout

```
apps/web/             Next.js application
services/api/         FastAPI application and trip-planning domain
services/worker/      Background price-search jobs (planned)
packages/shared/      Shared contracts (planned)
infra/                Infrastructure (planned)
.github/workflows/    CI workflows
```

## Getting started

Prerequisites: Node.js 22+, Python 3.12+, and Docker Desktop (optional).

1. Copy `.env.example` to `.env`. Add an `OPENAI_API_KEY` to enable AI extraction; without it, the API uses a basic deterministic fallback.
2. Start local infrastructure: `docker compose up -d db redis`.
3. Start the API:
   ```bash
   cd services/api
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
4. In another terminal, start the web app:
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```
5. Open http://localhost:3000. API docs are at http://localhost:8000/docs.

## Current MVP scope

- Natural-language trip request form.
- Structured trip-preference schema with origin, destination, date windows, trip duration, budget scope, airline and hotel preferences.
- AI-assisted extraction with a deterministic fallback.
- Separate hard constraints from soft preferences (for example, "nonstop only" versus "prefer nonstop").
- Clarification questions when key details such as destination, travel year, or budget scope are missing.
- Date handling that preserves broad windows like "March 2027" instead of inventing a specific day.
- API health and trip-intent endpoints.

The current trip-intent interpreter can identify explicit dates and date ranges, broad month/season windows, trip length, budget scope, airline exclusions/preferences, stop limits, departure/arrival periods, and hotel transit/chain preferences. It also returns clarification questions when information is missing. Live flight/hotel provider integrations, date-combination search, persisted accounts, price alerts, and award inventory are future milestones. Until providers are connected, the application labels its output as preference-understanding only and does not present mock data as live prices.

## Roadmap

1. **Foundation:** web app, API, schemas, local infrastructure, CI.
2. **Trip understanding:** natural-language extraction and editable structured preferences.
3. **Provider integrations:** live flight and accommodation search with normalized results.
4. **Optimization:** date-window exploration and combined flight + hotel ranking.
5. **Rewards:** loyalty profiles, award search, transfer-partner rules, redemption valuation.
6. **Personalization:** saved trips, alerts, and conversational refinement.

## Security

Do not commit `.env`, API keys, provider credentials, or personal loyalty account login credentials. Points balances can be entered manually; future integrations should use authorized provider flows and minimum necessary data.

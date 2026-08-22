# WanderWise

WanderWise turns a destination, a trip length, and a "vibe" (nature, historical, shopping, spiritual, and a few others) into a day-by-day itinerary of real places, real addresses, grouped into Day 1 / Day 2 / Day 3 tabs, with directions links you can actually click.

It's built as a small [LangGraph](https://langchain-ai.github.io/langgraph/) agent behind a FastAPI backend, with a plain HTML/CSS/JS frontend (no React, no build step).

I built this mainly to actually learn how agentic systems work in practice — chaining reasoning across multiple stateful steps instead of firing off one LLM call and formatting the output.

But the real itch was narrower: most "AI" travel and geolocation tools are just a chat wrapper in front of Google Maps. You ask, it searches, it summarizes — the model isn't doing anything Maps couldn't already do on its own, faster. I wanted to see what happens if the model actually does something with the geodata instead of just fetching and restating it: reranking places against a subjective "vibe" instead of a fixed category filter, reacting to live weather when choosing indoor vs. outdoor spots, deciding how to spread stops across multiple days. That reasoning layer is the part search-based tools skip entirely, and it's the part that felt worth actually building.

---

## What it does

1. You give it a location (typed, autocompleted, or "use my location"), a number of days, and a vibe.
2. It resolves the location and pulls current weather for context.
3. It queries the Geoapify Places API around that point, expanding the search radius if too few results come back.
4. Gemini reranks the raw place list against the selected vibe and filters out weak matches.
5. The survivors get distributed across the requested number of days and handed back as structured JSON, which the frontend renders as tabbed day cards.

---

## Architecture

The agent is a `StateGraph` with four nodes, each doing one job:

```
START → geo_weather_analysis → suggest_places → rank_places → rec_itinerary → END
```

| Node | File | Responsibility |
|---|---|---|
| `geo_weather_analysis` | `source/geoinput.py` | Resolves the location input and fetches current weather (OpenWeatherMap) so downstream nodes can react to it |
| `suggest_places` | `source/places.py` | Queries Geoapify Places, expanding the search radius when results are sparse |
| `rank_places` | `source/ranker.py` | Sends candidate places to Gemini along with the selected vibe, keeps the ones that actually fit |
| `rec_itinerary` | `source/itinerary.py` | Buckets ranked places into `Day 1..N` and writes the final recommendation text |

State is a `MemorySaver`-backed `AgentState` (Pydantic), threaded by a per-request `thread_id` — that's what lets a session get refined mid-conversation rather than starting over each call.

**A trade-off worth naming:** day distribution is currently a simple round-robin over the ranked place list, not a geographic clustering pass. It's deterministic and easy to reason about, but it means "Day 1" isn't guaranteed to be the places closest to each other — just the 1st, (N+1)th, (2N+1)th, etc. Fine for a first pass; geographic clustering per day is the obvious next improvement.

---

## Backend

FastAPI, three routes:

```
GET  /                  → serves the frontend
POST /api/itinerary     → runs the LangGraph agent, returns the structured plan
GET  /api/autocomplete  → proxies Geoapify's geocode/autocomplete for the location field
```

`WanderWiseAgent` (in `main.py`) owns the compiled graph and exposes `get_itinerary(query, location, vibe, days, user_id)` as the single entry point `app.py` calls into.

---

## Frontend

Plain HTML/CSS/JS, deliberately — this is a single form and a results view, not an app that needed a framework. A few things worth knowing if you're reading the code:

- Day tabs, vibe dropdown, and a numeric days input drive the request payload
- Location field has live autocomplete (debounced, hits `/api/autocomplete`) plus a "use my current location" geolocation button
- Light/dark theme toggle, persisted via `localStorage`

---

## Known limitations / what's next

- Day distribution is round-robin, not geography-aware — a Day 1 stop and a Day 3 stop could be next to each other while two Day 1 stops are across town from each other.
- No persistence beyond the in-memory `MemorySaver` checkpoint — sessions don't survive a server restart.
- No automated tests yet.
- Check for issues for more info.
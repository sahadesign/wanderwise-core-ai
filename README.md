# WanderWise AI 🌍🧠

> **An Intelligent Agentic Orchestrator for Real-time Travel Itinerary Synthesis**

Built using **LangGraph** and **Gemini 2.5 flash**, it moves beyond simple RAG (Retrieval-Augmented Generation) by implementing a **deterministic feedback loop** that intelligently expands search parameters to find the perfect travel spots, regardless of location density.

## Technical Architecture

The agent operates as a **Stateful Cyclic Graph**. Instead of a linear prompt, it follows a multi-stage reasoning process:

1.  **Contextual Awareness:** Fetches real-time weather data to influence recommendation logic (e.g., prioritizing indoor spots during rain).
2.  **Iterative Discovery:** Queries geospatial APIs with a dynamic radius.
3.  **Self-Correction Loop:** If result density is low, the agent triggers an "Expand Search" node, increasing the radius by 5km and retrying (up to 3 attempts).
4.  **Deterministic Guardrail:** Prevents LLM hallucinations in "Dead Zones" by bypassing synthesis if zero valid points of interest are found.
5.  **Vibe-Based Synthesis:** Personalizes tone and selection based on user "vibe" (Spiritual, Historical, Nature, etc.).

### System Flow
![Architecture Diagram](./architecture_flow.png)

## Tech Stack

- **Orchestration:** LangGraph (StateGraph)
- **LLM:** Google Gemini 2.5flash
- **Data Sources:** Geoapify (Places API), OpenWeatherMap (Real-time Weather)
- **Schema & Validation:** Pydantic
- **Environment:** Python 3.10+, Dotenv

## Key Breakthroughs

- **Hallucination Mitigation:** Implemented short-circuit logic that validates data presence before LLM invocation, ensuring 0% fake recommendations in sparse areas.
- **Resilient Search:** Built an automated retry mechanism that solved the "Rural Sparse Data" problem, increasing successful POI retrieval in non-urban areas.
- **Stateful Thread Management:** Uses `MemorySaver` to maintain conversation context and search history across multi-turn interactions.

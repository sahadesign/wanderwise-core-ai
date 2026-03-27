from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver

from pydantic import BaseModel
from typing import List, Dict, Literal
from dotenv import load_dotenv
import requests
import logging
import json
import os


logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("WanderWise")


# State definition
class AgentState(BaseModel):
    user_query: str
    user_location: str = ""
    user_vibe: str = "general"
    weather_context: str = ""
    nearby_places: List[dict] = []
    structured_plan: Dict[str, List[dict]] = {}
    radius: int = 5000
    retry_count: int = 0
    final_recommendation: str = ""


# The Wander Wise Agent Class
class WanderWiseAgent:
    VIBE_MAP = {
        "nature": "leisure.park,leisure.park.garden,natural.forest,natural.protected_area",
        "spiritual": "religion.place_of_worship,heritage",
        "shopping": "commercial.shopping_mall,commercial.marketplace",
        "historical": "heritage,building.historic,tourism.sights",
        "general": "tourism,entertainment,leisure",
    }

    def __init__(self, google_api_key: str, geo_api_key: str, weather_api_key: str):
        self.google_api_key = google_api_key
        self.geo_api_key = geo_api_key
        self.weather_api_key = weather_api_key

        self.memory = MemorySaver()
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", api_key=self.google_api_key
        )

        self.workflow = self._create_workflow()
        self.app = self.workflow.compile(checkpointer=self.memory)
        logger.info("Wander Wise Agent Core initialized")

    def _create_workflow(self) -> StateGraph:
        builder = StateGraph(AgentState)

        builder.add_node("geocode", self._geocoding_node)
        builder.add_node("fetch_weather", self._weather_node)
        builder.add_node("get_places", self._suggestions_node)
        builder.add_node("expand_search", self._expand_search_node)
        builder.add_node("rerank_results", self._reranker_node)
        builder.add_node("plan_itinerary", self._itinerary_planner_node)
        builder.add_node("llm_guide", self._llm_node)

        builder.add_edge(START, "geocode")
        builder.add_edge("geocode", "fetch_weather")
        builder.add_edge("fetch_weather", "get_places")

        builder.add_conditional_edges(
            "get_places",
            self._route_based_on_results,
            {"expand_search": "expand_search", "generate_guide": "rerank_results"},
        )

        builder.add_edge("expand_search", "get_places")
        builder.add_edge("rerank_results", "plan_itinerary")
        builder.add_edge("plan_itinerary", "llm_guide")
        builder.add_edge("llm_guide", END)

        return builder

    def _geocoding_node(self, state: AgentState):
        try:
            url = (
                f"https://api.geoapify.com/v1/geocode/search?"
                f"text={state.user_query}&apiKey={self.geo_api_key}"
            )
            data = requests.get(url).json()
            lon = data["features"][0]["properties"]["lon"]
            lat = data["features"][0]["properties"]["lat"]
            return {"user_location": f"{lat}, {lon}"}
        except Exception as e:
            logging.error(f"Geocoding failed: {e}")
            return {"user_location": "0,0"}

    def _weather_node(self, state: AgentState):
        """Fetches real-time weather data for a given 'latitude, longitude'."""
        try:
            if "," not in state.user_location:
                return {"weather_context": "Location invalid"}

            lat, lon = state.user_location.split(",")
            url = (
                f"https://api.openweathermap.org/data/2.5/weather?"
                f"lat={lat.strip()}&lon={lon.strip()}&"
                f"appid={self.weather_api_key}&"
                f"units=metric"
            )
            data = requests.get(url).json()
            weather = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            context = f"Current weather: {weather}, Temperature: {temp}°C"
            return {
                "weather_context": context,
                "radius": state.radius,
                "retry_count": state.retry_count,
            }
        except Exception as e:
            logger.error(f"Weather Fetch Failed: {e}")
            return {
                "weather_context": "Weather data unavailable",
                "radius": state.radius,
                "retry_count": state.retry_count,
            }

    def _suggestions_node(self, state: AgentState):
        """Fetches nearby travel spots/POIs within a 5km radius using Geoapify for a given 'latitude, longitude'"""
        try:
            lat, lon = state.user_location.split(",")
            categories = self.VIBE_MAP.get(
                state.user_vibe.lower(), self.VIBE_MAP["general"]
            )

            if state.retry_count > 0:
                categories += ",tourism.sights,entertainment.culture"

            url = (
                f"https://api.geoapify.com/v2/places?categories={categories}&"
                f"filter=circle:{lon.strip()},{lat.strip()},{state.radius}&"
                f"bias=proximity:{lon.strip()},{lat.strip()}&"
                f"limit=20&apiKey={self.geo_api_key}"
            )
            data = requests.get(url).json()
            places = data.get("features", [])

            existing_names = {p["name"] for p in state.nearby_places}
            unique_new = []
            for p in places:
                name = p["properties"].get("name")
                if name and name not in existing_names:
                    unique_new.append(
                        {
                            "name": name,
                            "distance_meters": p["properties"].get("distance"),
                            "address": p["properties"].get("address_line2"),
                        }
                    )
            return {"nearby_places": state.nearby_places + unique_new}

        except Exception as e:
            logger.error(f"Places Fetch Failed: {e}")
            return {"nearby_places": []}

    def _route_based_on_results(
        self, state: AgentState
    ) -> Literal["expand_search", "generate_guide"]:
        if len(state.nearby_places) >= 5:
            return "generate_guide"

        if state.retry_count < 3:
            return "expand_search"
        return "generate_guide"

    def _expand_search_node(self, state: AgentState):
        new_radius = state.radius + 5000
        logger.info(
            f"Expanding search to {new_radius}m (Retry: {state.retry_count + 1})"
        )
        return {"radius": new_radius, "retry_count": state.retry_count + 1}

    def _itinerary_planner_node(self, state: AgentState):
        sorted_spots = sorted(state.nearby_places, key=lambda x: x["distance_meters"])

        count = len(sorted_spots)
        morning_end = max(1, count // 3)
        afternoon_end = max(morning_end + 1, (2 * count) // 3)

        if count == 1:
            itinerary = {
                "Morning (9 AM - 12 PM)": [sorted_spots[0]],
                "Afternoon (1 PM - 5 PM)": [],
                "Evening (6 PM - 9 PM)": [],
            }
        elif count == 2:
            itinerary = {
                "Morning (9 AM - 12 PM)": [sorted_spots[0]],
                "Afternoon (1 PM - 5 PM)": [sorted_spots[1]],
                "Evening (6 PM - 9 PM)": [],
            }
        else:
            itinerary = {
                "Morning (9 AM - 12 PM)": sorted_spots[:morning_end],
                "Afternoon (1 PM - 5 PM)": sorted_spots[morning_end:afternoon_end],
                "Evening (6 PM - 9 PM)": sorted_spots[afternoon_end:],
            }

        logger.info(f"Structured itinerary planned with {len(sorted_spots)} spots.")
        return {"structured_plan": itinerary}

    def _reranker_node(self, state: AgentState):
        if not state.nearby_places:
            return {"nearby_places": []}

        places_list = [
            {"id": i, "name": p["name"], "address": p["address"]}
            for i, p in enumerate(state.nearby_places)
        ]

        prompt = f"""
        User Vibe: {state.user_vibe}
        Places to Evaluate: {places_list}

        Task: Assign a relevance score (1 - 10) based on how well each place fits the '{state.user_vibe}' vibe.
        - 8-10: Perfect fit (e.g., Temple for 'Spiritual').
        - 5-7: Acceptable/Neutral (e.g., A quiet park).
        - 1-4: Poor fit (e.g., A busy shopping mall for 'Spiritual').

        Return ONLY a JSON list of objects: [{{"id": 0, "score": 9}}, ...]
        """

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            raw_json = response.content.strip()
            if "```json" in raw_json:
                raw_json = raw_json.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_json:
                raw_json = raw_json.split("```")[1].split("```")[0].strip()

            scores = json.loads(raw_json)
            score_map = {item["id"]: item["score"] for item in scores}

            high_vibe_relevent_places = [
                p for i, p in enumerate(state.nearby_places) if score_map.get(i, 0) >= 6
            ]

            if len(high_vibe_relevent_places) < 3:
                logger.info("Strict filter too aggressive. Switching to top scorers.")
                sorted_by_score = sorted(
                    state.nearby_places,
                    key=lambda x: score_map.get(state.nearby_places.index(x), 0),
                    reverse=True,
                )
                high_vibe_relevent_places = sorted_by_score[:5]

            logger.info(
                f"Re-Ranker filtered {len(state.nearby_places)} spots down to {len(high_vibe_relevent_places)} high vibe matches."
            )
            return {"nearby_places": high_vibe_relevent_places}
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}. Falling back to original list")
            return {"nearby_places": state.nearby_places}

    def _llm_node(self, state: AgentState):
        if not state.nearby_places:
            return {
                "final_recommendation": (
                    f"Wander Wise AI: I've searched up to 20km around your location, "
                    f"but I couldn't find any spots matching the '{state.user_vibe}' vibe. "
                    f"The current weather is {state.weather_context}, but unfortunately, "
                    "there are no specific venues to recommend right now."
                )
            }

        plan_str = ""
        for time_slot, spots in state.structured_plan.items():
            plan_str += f"\{time_slot}:\n"
            for spot in spots:
                plan_str += f"- {spot['name']} ({spot['distance_meters']}m away)\n"

        status_msg = ""
        if state.retry_count >= 3 and len(state.nearby_places) < 10:
            status_msg = "Note: I searched upto 20km but found limited spots for this specific vibe"

        prompt = f"""
        {status_msg}
        Context:
        - User Vibe: {state.user_vibe}
        - Weather: {state.weather_context}
        - I have organized a logical, non-zig-zag route for the user:
        {plan_str}

        Role: You are Wander Wise AI. Write a friendly, cohesive daily guide. 
        1. Explain why the Morning spots are a great start.
        2. Reference the weather for the Afternoon (e.g., if it's hot, mention staying cool).
        3. Keep the tone matching the '{state.user_vibe}' vibe.
        """
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return {"final_recommendation": response.content}

    def get_itinerary(self, location: str, vibe: str, user_id: str):
        config = {"configurable": {"thread_id": user_id}}
        inputs = {"user_location": location, "user_vibe": vibe}
        return self.app.invoke(inputs, config)


if __name__ == "__main__":
    load_dotenv()

    # Initialize the Agent
    agent = WanderWiseAgent(
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        geo_api_key=os.getenv("GEOAPIFY_API_KEY"),
        weather_api_key=os.getenv("OPENWEATHER_API_KEY"),
    )

    test_scenarios = [
        {
            "name": "METRO_DENSE (Bengaluru)",
            "location": "12.9716,77.5946",
            "vibe": "nature",
        },
        {
            "name": "RURAL_SPARSE (Hassan)",
            "location": "13.0033,76.1017",
            "vibe": "historical",
        },
        {
            "name": "THE_DEAD_ZONE (Thar Desert)",
            "location": "27.0000,71.0000",
            "vibe": "shopping",
        },
        {
            "name": "VIBE_PIVOT (Spiritual)",
            "location": "12.9716,77.5946",
            "vibe": "spiritual",
        },
    ]

    for scenario in test_scenarios:
        print(f"\n{'-'*20} RUNNING TEST: {scenario['name']} {'-'*20}")

        result = agent.get_itinerary(
            location=scenario["location"],
            vibe=scenario["vibe"],
            user_id=scenario["name"],
        )

        print(f"Final Radius Reached: {result.get('radius', 5000)}m")
        print("LOGISTICS CHECK (Structured Plan):")
        plan = result.get("structured_plan", {})
        for slot, spots in plan.items():
            names = [s["name"] for s in spots]
            print(f"  {slot}: {', '.join(names) if names else 'Empty'}")
        print(f"Total Spots Found: {len(result.get('nearby_places', []))}")
        print("-" * 10)
        print(f"Wander Wise Recommendation:\n{result['final_recommendation']}")

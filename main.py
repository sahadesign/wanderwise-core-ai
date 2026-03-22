from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver

from pydantic import BaseModel
from typing import List, Literal, Annotated
from dotenv import load_dotenv
from operator import add
import requests
import logging
import os


logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("WanderWise")


# State definition
class AgentState(BaseModel):
    user_location: str
    user_vibe: str = "general"
    weather_context: str = ""
    nearby_places: Annotated[List[dict], add] = []
    radius: int = 5000
    retry_count: int = 0
    final_recommendation: str = ""


# The Wander Wise Agent Class
class WanderWiseAgent:
    VIBE_MAP = {
        "spiritual": "religion.place_of_worship,heritage",
        "nature": "natural,leisure.park,camping",
        "shopping": "commercial.shopping_mall,leisure.market",
        "historical": "heritage,tourism.sights",
        "general": "tourism,leisure,entertainment",
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

        builder.add_node("fetch_weather", self._weather_node)
        builder.add_node("get_places", self._suggestions_node)
        builder.add_node("expand_search", self._expand_search_node)
        builder.add_node("llm_guide", self._llm_node)

        builder.add_edge(START, "fetch_weather")
        builder.add_edge("fetch_weather", "get_places")

        builder.add_conditional_edges(
            "get_places",
            self._route_based_on_results,
            {"expand_search": "expand_search", "generate_guide": "llm_guide"},
        )

        builder.add_edge("expand_search", "get_places")
        builder.add_edge("llm_guide", END)

        return builder

    def _weather_node(self, state: AgentState):
        """Fetches real-time weather data for a given 'latitude, longitude'."""
        try:
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
                "retry_count": state.retry_count
            }
        except Exception as e:
            logger.error(f"Weather Fetch Failed: {e}")
            return {
                "weather_context": "Weather data unavailable",
                "radius": state.radius,
                "retry_count": state.retry_count
            }

    def _suggestions_node(self, state: AgentState):
        """Fetches nearby travel spots/POIs within a 5km radius using Geoapify for a given 'latitude, longitude'"""
        try:
            lat, lon = state.user_location.split(",")
            categories = self.VIBE_MAP.get(
                state.user_vibe.lower(), self.VIBE_MAP["general"]
            )
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
            return {"nearby_places": unique_new}

        except Exception as e:
            logger.error(f"Places Fetch Failed: {e}")
            return {"nearby_places": []}

    def _route_based_on_results(
        self, state: AgentState
    ) -> Literal["expand_search", "generate_guide"]:
        if len(state.nearby_places) < 10 and state.retry_count < 3:
            return "expand_search"
        return "generate_guide"

    def _expand_search_node(self, state: AgentState):
        new_radius = state.radius + 5000
        logger.info(
            f"Expanding search to {new_radius}m (Retry: {state.retry_count + 1})"
        )
        return {"radius": new_radius, "retry_count": state.retry_count + 1}

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

        sorted_places = sorted(state.nearby_places, key=lambda x: x["distance_meters"])[
            :10
        ]

        status_msg = ""
        if state.retry_count >= 3 and len(state.nearby_places) < 10:
            status_msg = "Note: I searched upto 20km but found limited spots for this specific vibe"

        prompt = f"""
        {status_msg}
        Context:
        - User Vibe: {state.user_vibe}
        - Weather: {state.weather_context}
        - Top 10 Nearby Spots: {sorted_places}

        Role: You are Wander Wise AI. Create a 'vibe-based' itinerary recommendation. 
        Strict Rule: ONLY recommend places listed in the 'Top 10 Nearby Spots' above. 
        If the list has fewer than 10 spots, only talk about those. Do not invent new ones.
        
        If vibe is 'spiritual', be respectful. If 'shopping', be energetic.
        If it's 'raining', suggest indoor spots. If 'sunny', suggest parks.
        List the spots with their distances.
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
            user_id=scenario["name"] 
        )

        print(f"Final Radius Reached: {result.get('radius', 5000)}m")
        print(f"Total Spots Found: {len(result.get('nearby_places', []))}")
        print("-" * 10)
        print(f"Wander Wise Recommendation:\n{result['final_recommendation']}")

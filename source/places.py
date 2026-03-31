import os
import requests
from .state import AgentState
from dotenv import load_dotenv


class Suggestions:
    def __init__(self, geo_api_key: str):
        self.geo_api_key = geo_api_key

    VIBE_MAP = {
        "nature": "leisure.park,leisure.park.garden,natural.forest,natural.protected_area",
        "spiritual": "religion.place_of_worship,heritage",
        "shopping": "commercial.shopping_mall,commercial.marketplace",
        "historical": "heritage,building.historic,tourism.sights",
        "general": "tourism,entertainment,leisure",
    }

    def fetch_places(self, state: AgentState):
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
                if name and not any(name in existing for existing in existing_names):
                    unique_new.append(
                        {
                            "name": name,
                            "address": p["properties"].get("address_line2"),
                            "lat": p["properties"].get("lat"),
                            "lon": p["properties"].get("lon"),
                            "distance_meters": p["properties"].get("distance"),
                            "place_id": p["properties"].get("place_id"),
                        }
                    )
            state.nearby_places = state.nearby_places + unique_new
        except Exception as e:
            print(f" ERROR - Fetching places failed: {e}")

    def expand_search(self, state: AgentState):
        state.radius += 5000
        state.retry_count += 1
        print(
            f"INFO - Expanding search to {state.radius}m (Retry: {state.retry_count})"
        )


def places(state: AgentState):
    load_dotenv()
    p = Suggestions(geo_api_key=os.getenv("GEOAPIFY_API_KEY"))

    while len(state.nearby_places) < 5 and state.retry_count < 3:
        p.fetch_places(state)

        if len(state.nearby_places) < 5:
            p.expand_search(state)
        else:
            break

    return state

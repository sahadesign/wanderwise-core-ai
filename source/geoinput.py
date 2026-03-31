import os
import requests
from .state import AgentState
from dotenv import load_dotenv


class GeolocationAndWeather:
    def __init__(self, geo_api_key: str, weather_api_key: str):
        self.geo_api_key = geo_api_key
        self.weather_api_key = weather_api_key

    def _geo_location(self, state: AgentState):
        try:
            if "," in state.user_query and any(
                char.isdigit() for char in state.user_query
            ):
                print(f"INFO - Using direct coordinates: {state.user_query}")
                state.user_location = state.user_query
                return

            url = (
                f"https://api.geoapify.com/v1/geocode/search?"
                f"text={state.user_query}&apiKey={self.geo_api_key}"
            )
            data = requests.get(url).json()
            lon = data["features"][0]["properties"]["lon"]
            lat = data["features"][0]["properties"]["lat"]
            state.user_location = f"{lat}, {lon}"
        except Exception as e:
            print(f"ERROR - Fetching location failed: {e}")
            state.user_location = "0,0"

    def _fetch_weather(self, state: AgentState):
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
            state.weather_context = f"Current weather: {weather}, Temperature: {temp}°C"
        except Exception as e:
            print(f"ERROR - Weather Fetch Failed: {e}")
            state.weather_context = "Weather data unavailable"


def geoinput(state: AgentState):
    load_dotenv()
    gl = GeolocationAndWeather(
        geo_api_key=os.getenv("GEOAPIFY_API_KEY"),
        weather_api_key=os.getenv("OPENWEATHER_API_KEY"),
    )

    gl._geo_location(state)
    gl._fetch_weather(state)

    return {
        "user_location": state.user_location,
        "weather_context": state.weather_context,
    }

import uuid
from pathlib import Path

import os
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from main import WanderWiseAgent

app = FastAPI()
agent = WanderWiseAgent()

app.mount("/static", StaticFiles(directory="ui"), name="static")


class TripRequest(BaseModel):
    query: str
    location: str
    vibe: str = "General"
    days: int = 1


@app.get("/")
def home():
    return FileResponse(Path("ui/index.html"))


@app.post("/api/itinerary")
def create_itinerary(request: TripRequest):
    result = agent.get_itinerary(
        query=request.query,
        location=request.location,
        vibe=request.vibe.lower(),
        days=request.days,
        user_id=str(uuid.uuid4()),
    )
    return result


@app.get("/api/autocomplete")
def autocomplete(query: str = ""):
    api_key = os.getenv("GEOAPIFY_API_KEY")
    url = f"https://api.geoapify.com/v1/geocode/autocomplete?text={query}&format=json&apiKey={api_key}"
    response = requests.get(url)
    return response.json()

# app.py
import uuid
from pathlib import Path

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


@app.get("/")
def home():
    return FileResponse(Path("ui/index.html"))


@app.post("/api/itinerary")
def create_itinerary(request: TripRequest):
    result = agent.get_itinerary(
        query=request.query,
        location=request.location,
        vibe=request.vibe.lower(),
        user_id=str(uuid.uuid4()),
    )
    return result

from pydantic import BaseModel
from typing import List, Dict


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
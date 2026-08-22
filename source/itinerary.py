from .LLM import LLM
from .state import AgentState
from langchain_core.messages import HumanMessage


class Itinerary:
    def __init__(self):
        self.llm = LLM()

    def _itinerary_plan(self, state: AgentState):
        sorted_spots = sorted(state.nearby_places, key=lambda x: x["distance_meters"])
        target_days = max(1, state.days)

        itinerary = {f"Day {i}": [] for i in range(1, target_days + 1)}

        for index, spot in enumerate(sorted_spots):
            day_index = (index % target_days) + 1
            itinerary[f"Day {day_index}"].append(spot)

        print(
            f"INFO - Structured multi-day itinerary planned across {target_days} days with {len(sorted_spots)} total spots."
        )
        state.structured_plan = itinerary
        return state

    def get_llm_response(self, state: AgentState):
        state = self._itinerary_plan(state)

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
        Context:
        - User Vibe: {state.user_vibe}
        - Weather: {state.weather_context}
        - Route Plan:
        {plan_str}

        Role: You are Wander Wise AI. A helpful, cheery and confident Travel & Itinerary Planner
        Task 1: For each location listed above, write a short, compelling, and specific 1-sentence description tailored to the '{state.user_vibe}' vibe and current weather.
        
        Task 2: Write a concise, actionable 2-3 sentence overview/recommendation for the entire trip that gives practical timing or pacing advice.

        Return ONLY valid JSON in this exact structure:
        {{
          "spot_descriptions": {{
            "Exact Spot Name 1": "Custom tailored description here...",
            "Exact Spot Name 2": "Custom tailored description here..."
          }},
          "final_recommendation": "Actionable trip overview here..."
        }}
        """
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content
            if isinstance(content, list):
                raw_text = "".join(
                    [
                        (
                            item.get("text", str(item))
                            if isinstance(item, dict)
                            else str(item)
                        )
                        for item in content
                    ]
                )
            elif isinstance(content, dict):
                raw_text = content.get("text", str(content))
            else:
                raw_text = str(content)

            raw_text = raw_text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            import json

            parsed_data = json.loads(raw_text)
            descriptions = parsed_data.get("spot_descriptions", {})
            final_rec = parsed_data.get(
                "final_recommendation", "Enjoy your customized trip!"
            )

            for day, spots in state.structured_plan.items():
                for spot in spots:
                    name = spot["name"]
                    if name in descriptions:
                        spot["category"] = descriptions[name]

            return {
                "structured_plan": state.structured_plan,
                "final_recommendation": final_rec,
            }
        except Exception as e:
            print(f"ERROR - LLM Enrichment failed: {e}. Keeping default details.")
            return {
                "structured_plan": state.structured_plan,
                "final_recommendation": "Enjoy your customized journey across these curated destinations.",
            }


def itinerary(state: AgentState):
    it = Itinerary()
    return it.get_llm_response(state)

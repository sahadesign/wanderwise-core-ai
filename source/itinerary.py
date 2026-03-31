from .LLM import LLM
from .state import AgentState
from langchain_core.messages import HumanMessage


class Itinerary:
    def __init__(self):
        self.llm = LLM()

    def _itinerary_plan(self, state: AgentState):
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

        print(f"INFO - Structured itinerary planned with {len(sorted_spots)} spots.")
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
        return {
            "structured_plan": state.structured_plan,
            "final_recommendation": response.content,
        }


def itinerary(state: AgentState):
    it = Itinerary()
    return it.get_llm_response(state)

import json
from .LLM import LLM
from .state import AgentState
from langchain_core.messages import HumanMessage


class Ranker:
    def __init__(self, state: AgentState):
        places_list = [
            {"id": i, "name": p["name"], "address": p["address"]}
            for i, p in enumerate(state.nearby_places)
        ]
        self.prompt = f"""
        User Vibe: {state.user_vibe}
        Places to Evaluate: {places_list}

        Task: Assign a relevance score (1 - 10) based on how well each place fits the '{state.user_vibe}' vibe.
        - 8-10: Perfect fit (e.g., Temple for 'spiritual').
        - 5-7: Acceptable/Neutral (e.g., A quiet park for 'nature').
        - 1-4: Poor fit (e.g., A busy shopping mall for 'Spiritual').

        Return ONLY a JSON list of objects: [{{"id": 0, "score": 9}}, ...]
        """

    def rank_places(self, state: AgentState):
        try:
            if not state.nearby_places:
                state.nearby_places = []

            llm = LLM()
            response = llm.invoke([HumanMessage(content=self.prompt)])
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
                print("INFO - Strict filter too aggressive. Switching to top scorers.")
                sorted_by_score = sorted(
                    state.nearby_places,
                    key=lambda x: score_map.get(state.nearby_places.index(x), 0),
                    reverse=True,
                )
                high_vibe_relevent_places = sorted_by_score[:5]

            print(
                f"INFO - Re-Ranker filtered {len(state.nearby_places)} spots down to {len(high_vibe_relevent_places)} high vibe matches."
            )
            state.nearby_places = high_vibe_relevent_places
        except Exception as e:
            print(f" ERROR - Re-ranking failed: {e}. Falling back to original list")
            state.nearby_places = state.nearby_places


def ranker(state: AgentState):
    r = Ranker(state)
    r.rank_places(state)

    return state
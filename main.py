import uuid
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Import your state and modular nodes
from source.state import AgentState
from source.geoinput import geoinput
from source.places import places
from source.ranker import ranker
from source.itinerary import itinerary


class WanderWiseAgent:
    def __init__(self):
        load_dotenv()
        self.memory = MemorySaver()
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile(checkpointer=self.memory)
        print("INFO - Modular Wander Wise Agent initialized")

    def _create_workflow(self) -> StateGraph:
        builder = StateGraph(AgentState)

        builder.add_node("geo_weather_analysis", geoinput)
        builder.add_node("suggest_places", places)
        builder.add_node("rank_places", ranker)
        builder.add_node("rec_itinerary", itinerary)

        builder.add_edge(START, "geo_weather_analysis")
        builder.add_edge("geo_weather_analysis", "suggest_places")
        builder.add_edge("suggest_places", "rank_places")
        builder.add_edge("rank_places", "rec_itinerary")
        builder.add_edge("rec_itinerary", END)

        return builder

    def get_itinerary(self, query: str, location: str, vibe: str, user_id: str):
        config = {"configurable": {"thread_id": user_id}}
        inputs = {"user_query": query, "user_location": location, "user_vibe": vibe}
        return self.app.invoke(inputs, config)


if __name__ == "__main__":
    agent = WanderWiseAgent()

    test_scenarios = [
        {
            "name": "Bengaluru",
            "location": "12.9716,77.5946",
            "vibe": "nature",
        },
        {
            "name": "Hassan",
            "location": "13.0033,76.1017",
            "vibe": "historical",
        },
        {
            "name": "Thar Desert",
            "location": "27.0000,71.0000",
            "vibe": "shopping",
        },
        {
            "name": "Bengaluru",
            "location": "12.9716,77.5946",
            "vibe": "spiritual",
        },
    ]

    for scenario in test_scenarios:
        print(f"\n{'-'*20} RUNNING TEST: {scenario['name']} {'-'*20}")

        random_user_id = str(uuid.uuid4())
        result = agent.get_itinerary(
            query=scenario["name"],
            location=scenario["location"],
            vibe=scenario["vibe"],
            user_id=random_user_id,
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

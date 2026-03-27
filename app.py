import os
from dotenv import load_dotenv
import chainlit as cl
from chainlit.input_widget import Select
from main import WanderWiseAgent

load_dotenv()

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Try for Free: Plan a Trip 🎒",
            message="Help me plan a 3-day trip to a hidden gem!",
        ),
        cl.Starter(
            label="Search by Vibe ✨",
            message="Suggest a spiritual retreat near the mountains.",
        ),
    ]

@cl.on_settings_update
async def setup_agent(settings):
    # Store settings in session so cl.on_message can see them
    cl.user_session.set("settings", settings)
    await cl.Message(content=f"Vibe updated to: {settings['Vibe']}").send()

@cl.on_chat_start
async def start():
    # 1. Setup the Brand "Vibe" Selector in Sidebar
    await cl.ChatSettings(
        [
            Select(
                id="Vibe",
                label="Choose your Vibe",
                values=["Nature 🌿", "Spiritual 🧘", "Shopping 🛍️", "Historical 🏛️"],
                initial_index=0,
            )
        ]
    ).send()

    # 2. Initialize your Agent
    agent = WanderWiseAgent(
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        geo_api_key=os.getenv("GEOAPIFY_API_KEY"),
        weather_api_key=os.getenv("OPENWEATHER_API_KEY"),
    )
    cl.user_session.set("agent", agent)


@cl.on_message
async def main(message: cl.Message):
    agent = cl.user_session.get("agent")
    settings = cl.user_session.get("chat_settings")
    vibe = settings.get("Vibe", "general").split(" ")[0].lower()

    config = {"configurable": {"thread_id": cl.user_session.get("id")}}

    initial_state = {
        "user_query": message.content,
        "user_vibe": vibe,
        "nearby_places": [],
        "structured_plan": {},
    }
    recommendation_text = "I couldn't generate a plan. Please try again!"
    async with cl.Step(name="WanderWise Journey") as parent_step:
        parent_step.input = message.content

        async for event in agent.app.astream(initial_state, config=config):
            for node_name, output in event.items():
                if node_name == "llm_guide":
                    final_output = output.get("final_recommendation", "")
                    cl.user_session.set("final_output", final_output)

                async with cl.Step(
                    name=node_name, parent_id=parent_step.id
                ) as node_step:
                    if node_name == "geocode":
                        location = output.get("user_location", "Unknown")
                        node_step.output = f"🌎 Located destination at: {location}"

                    elif node_name == "get_weather":
                        weather = output.get("weather_context", "Checking...")
                        node_step.output = f"☀️ Weather Check: {weather}"

                    elif node_name == "fetch_nearby_places":
                        count = len(output.get("nearby_places", []))
                        node_step.output = f"📍 Found {count} potential spots."

                    elif node_name == "rerank_results":
                        node_step.output = (
                            f"⚖️ Scoring results against your '{vibe}' vibe."
                        )

                    elif node_name == "generate_itinerary":
                        node_step.output = "📝 Synthesizing your final travel plan..."

                    else:
                        # Falling back for any other nodes in graph
                        node_step.output = f"Successfully executed {node_name}."

    final_itinerary = cl.user_session.get("final_output")
    if final_itinerary:
        await cl.Message(content=final_itinerary).send()
    else:
        await cl.Message(content=recommendation_text).send()

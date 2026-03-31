import json
import requests
import chainlit as cl
from langchain_core.messages import HumanMessage

from source.LLM import LLM


async def get_intent(query):
    llm = LLM()
    prompt = f"""
    Analyze: "{query}"
    Extract the destination and vibe based on user's prompt. 
    If no city is mentioned, set location to "DETECT".
    Return ONLY a JSON object.
    JSON format: {{
        "location": "city_name_or_DETECT", 
        "vibe": "nature/spiritual/shopping/historical/general"
    }}
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    raw_content = response.content.strip()

    if "```json" in raw_content:
        raw_content = raw_content.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_content:
        raw_content = raw_content.split("```")[1].split("```")[0].strip()

    try:
        intent_data = json.loads(raw_content)

        print(f"\n{'='*10} LLM INTENT {'='*10}")
        print(f"User Query: {query}")
        print(f"Extracted Location: {intent_data.get('location')}")
        print(f"Extracted Vibe: {intent_data.get('vibe')}")
        print(f"{'='*30}\n")

        return intent_data
    except json.JSONDecodeError as e:
        print(f"ERROR - Failed to parse intent: {raw_content}")
        return {"location": "DETECT", "vibe": "general"}


def get_ip_coordinates():
    """Fetches approximate lat/lon with a fallback API."""
    # Try the first provider
    providers = ["http://ip-api.com/json/", "https://ipapi.co/json/"]

    for url in providers:
        try:
            print(f"INFO - Attempting geolocation via: {url}")
            response = requests.get(url, timeout=5)
            data = response.json()

            lat = data.get("lat") or data.get("latitude")
            lon = data.get("lon") or data.get("longitude")
            city = data.get("city")

            if lat and lon:
                print(f"INFO - Geolocation Success: {city} ({lat}, {lon})")
                return f"{lat}, {lon}"
        except Exception as e:
            print(f"INFO - Connection to {url} failed: {e}")
            continue

    return None


async def run_agent(location, vibe, original_message):
    agent = cl.user_session.get("agent")

    settings = cl.user_session.get("settings") or {"Vibe": "Nature 🌿"}
    vibe = vibe.split(" ")[0].lower() if vibe else "nature"

    config = {"configurable": {"thread_id": cl.user_session.get("id")}}
    initial_state = {"user_query": location, "user_vibe": vibe}

    final_places = []
    recommendation_text = "I couldn't generate a plan. Please try again!"

    async with cl.Step(name="WanderWise Journey") as parent_step:
        parent_step.input = f"Location: {location} (Vibe: {vibe})"

        async for event in agent.app.astream(initial_state, config=config):
            for node_name, output in event.items():
                if "nearby_places" in output:
                    final_places = output["nearby_places"]

                if "final_recommendation" in output:
                    recommendation_text = output["final_recommendation"]

                async with cl.Step(
                    name=node_name, parent_id=parent_step.id
                ) as node_step:
                    if node_name == "geo_weather_analysis":
                        loc = output.get("user_location", "Searching...")
                        node_step.output = f"🌎 Analysis complete for: {loc}"

                    elif node_name == "suggest_places":
                        count = len(output.get("nearby_places", []))
                        node_step.output = f"📍 Discovered {count} spots in the area."

                    elif node_name == "rank_places":
                        node_step.output = f"⚖️ Filtering for the best '{vibe}' matches."

                    elif node_name == "rec_itinerary":
                        node_step.output = "📝 Crafting your personalized guide..."

                    else:
                        node_step.output = f"Executed {node_name}"

    elements = []
    for place in final_places:
        elements.append(
            cl.Text(
                name=place["name"],
                content=f"📍 Address: {place['address']}\n📏 Distance: {place['distance_meters']}m",
                display="inline",
            )
        )
    await cl.Message(
        author="WanderWise AI", content=recommendation_text, elements=elements
    ).send()

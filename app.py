from dotenv import load_dotenv
import chainlit as cl
from chainlit.input_widget import Select
from engineio.payload import Payload

import ui.helper
from main import WanderWiseAgent

load_dotenv()
Payload.max_decode_packets = 500


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


@cl.on_chat_start
async def start():
    cl.Image(name="WanderWise AI", path="./public/logo_light.svg", type="avatar")
    await cl.ChatSettings(
        [
            Select(
                id="Vibe",
                label="Choose your Vibe",
                values=[
                    "General 👀",
                    "Nature 🌿",
                    "Spiritual 🧘",
                    "Shopping 🛍️",
                    "Historical 🏛️",
                ],
                initial_index=0,
            )
        ]
    ).send()

    status_msg = cl.Message(content="Vibe: General 👀")
    await status_msg.send()
    cl.user_session.set("status_msg_id", status_msg.id)

    agent = WanderWiseAgent()
    cl.user_session.set("agent", agent)


@cl.on_settings_update
async def setup_agent(settings):
    cl.user_session.set("settings", settings)
    msg_id = cl.user_session.get("status_msg_id")
    if msg_id:
        await cl.Message(
            id=msg_id, content=f"Vibe: **{settings['Vibe']}**"
        ).update()


@cl.action_callback("gps_button")
async def on_action(action: cl.Action):
    vibe = cl.user_session.get("current_vibe") or "nature"
    action_value = action.payload.get("value")

    if action.forId:
        await cl.Message(
            id=action.forId, content="Selection received!", actions=[]
        ).update()

    if action_value == "allow":
        msg = cl.Message(content="🛰️ WanderWise is fetching your location via IP...")
        await msg.send()

        coords = ui.helper.get_ip_coordinates()
        if coords:
            msg.content = (
                f"📍 Location identified ({coords}). Finding '{vibe}' spots..."
            )
            await msg.update()
        else:
            # This part is CRITICAL when the API times out
            msg.content = "⚠️ Sorry, I couldn't detect your location automatically."
            await msg.update()

            res = await cl.AskUserMessage(
                content="Please type your city name:", timeout=30
            ).send()

            if res:
                await ui.helper.run_agent(res["output"], vibe, None)
    elif action_value == "deny":
        res = await cl.AskUserMessage(
            content="Please type your city name:", timeout=30
        ).send()
        if res:
            await ui.helper.run_agent(res["output"], vibe, None)


@cl.on_message
async def main(message: cl.Message):
    query = await ui.helper.get_intent(message.content)
    vibe = query.get("vibe", "nature")
    cl.user_session.set("current_vibe", vibe)

    if query["location"] == "DETECT":
        actions = [
            cl.Action(
                name="gps_button",
                label="Allow GPS 📍",
                payload={"value": "allow"},
            ),
            cl.Action(
                name="gps_button",
                label="Type manually ⌨️",
                payload={"value": "deny"},
            ),
        ]
        await cl.Message(
            content="I noticed you didn't specify a place. Can I use your current location?",
            actions=actions,
        ).send()
    else:
        await ui.helper.run_agent(query["location"], vibe, message)

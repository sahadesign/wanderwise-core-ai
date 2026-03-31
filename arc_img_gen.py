import os
from dotenv import load_dotenv
from main import WanderWiseAgent
load_dotenv()

def generate_diagram(agent_app, filename="architecture_flow.png"):
    try:
        png_bytes = agent_app.get_graph().draw_mermaid_png()
        
        with open(filename, "wb") as f:
            f.write(png_bytes)
        print(f"Architecture diagram saved as {filename}")
        
    except Exception as e:
        print(f"Could not generate PNG: {e}")
        print(agent_app.get_graph().draw_mermaid())


agent = WanderWiseAgent()

generate_diagram(agent.app)
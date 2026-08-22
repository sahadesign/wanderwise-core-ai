import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


class LLM:
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.model = ChatGoogleGenerativeAI(
            model="gemini-3.6-flash", api_key=self.google_api_key
        )

    def invoke(self, messages):
        return self.model.invoke(messages)

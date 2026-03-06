from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI

from app.tools import search_candidates
from app.config import GOOGLE_API_KEY


def build_agent():

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite-preview",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1
    )

    tools = [search_candidates]

    system_prompt = (
        "You are an intelligent, conversational AI recruiter assistant. "
        "You help users find candidates based on available resume data. "
        "If the user asks a general question, answer them conversationally. "
        "If the user asks to find, search, or look up candidates, ALWAYS use the `search_candidates` tool. "
        "When you use the tool, briefly summarize your findings in a natural, friendly way. "
        "DO NOT list the raw JSON output of candidates in your text response, as the UI will render the candidate cards separately."
    )
    
    memory = MemorySaver()

    return create_react_agent(llm, tools, prompt=system_prompt, checkpointer=memory)
import os
import json
from typing import Optional, List

import google.generativeai as genai
from fastapi import FastAPI
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    Range,
    MatchValue,
)

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

# ==================================================
# CONFIG
# ==================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "resumes"

genai.configure(api_key=GEMINI_API_KEY)

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0,
)

EMBEDDING_MODEL = "models/embedding-001"

app = FastAPI()


# ==================================================
# EMBEDDING
# ==================================================

def embed_query(text: str) -> List[float]:
    response = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query",
    )

    embedding = response["embedding"]

    norm = sum(x * x for x in embedding) ** 0.5
    if norm > 0:
        embedding = [x / norm for x in embedding]

    return embedding


# ==================================================
# TOOL INPUT
# ==================================================

class ResumeSearchInput(BaseModel):
    query_text: str = Field(...)
    min_experience: Optional[float] = None
    city: Optional[str] = None
    skills: Optional[List[str]] = None


# ==================================================
# FILTER BUILDER
# ==================================================

def build_filter(min_experience, city, skills):
    must_conditions = []

    if min_experience is not None:
        must_conditions.append(
            FieldCondition(
                key="total_experience",
                range=Range(gte=min_experience),
            )
        )

    if city:
        must_conditions.append(
            FieldCondition(
                key="city",
                match=MatchValue(value=city),
            )
        )

    if skills:
        for skill in skills:
            must_conditions.append(
                FieldCondition(
                    key="skills",
                    match=MatchValue(value=skill),
                )
            )

    return Filter(must=must_conditions) if must_conditions else None


# ==================================================
# SEARCH TOOL
# ==================================================

@tool(args_schema=ResumeSearchInput)
def search_resumes(
    query_text: str,
    min_experience: Optional[float] = None,
    city: Optional[str] = None,
    skills: Optional[List[str]] = None,
):
    query_vector = embed_query(query_text)
    query_filter = build_filter(min_experience, city, skills)

    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=query_filter,
        limit=10,
    )

    formatted = []
    for r in results:
        payload = r.payload
        formatted.append(
            {
                "score": r.score,
                "name": payload.get("name"),
                "title": payload.get("current_job_title"),
                "experience": payload.get("total_experience"),
                "skills": payload.get("skills"),
                "city": payload.get("city"),
            }
        )

    return json.dumps(formatted)


# ==================================================
# AGENT
# ==================================================

SYSTEM_PROMPT = """
You are an AI recruitment search agent.

Extract:
- skills
- min_experience
- city

Always call search_resumes tool.
"""

agent = create_react_agent(
    llm=llm,
    tools=[search_resumes],
    system_prompt=SYSTEM_PROMPT,
)


# ==================================================
# API
# ==================================================

class SearchRequest(BaseModel):
    query: str


@app.post("/search")
def search(request: SearchRequest):
    response = agent.invoke(
        {"messages": [HumanMessage(content=request.query)]}
    )
    return {"result": response}
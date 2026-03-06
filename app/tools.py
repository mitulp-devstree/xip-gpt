import json
from langchain.tools import tool
from app.vector_store import search_vector


@tool
def search_candidates(query: str, limit: int = 10):
    """Search for matching candidates in the vector store based on the given query.
    
    Args:
        query: The search query string describing the candidates.
        limit: The maximum number of candidates to return. Default is 10. Increase this if the user asks for more (e.g. 50).
    """
    results = search_vector(query, limit=limit)

    return json.dumps(results)

@tool
def submit_candidates(candidates: list[dict]):
    """Submit the curated, evaluated, and ranked candidate list to the UI.
    
    Args:
        candidates: A list of candidate dictionaries. You must use this tool to display the final curated results to the user!
    """
    return json.dumps(candidates)
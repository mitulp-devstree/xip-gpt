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
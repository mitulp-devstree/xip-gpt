from google import genai
from google.genai import types
from app.config import GOOGLE_API_KEY

client = genai.Client(api_key=GOOGLE_API_KEY)

MODEL = "gemini-embedding-001"


def embed_text(text: str):

    response = client.models.embed_content(
        model=MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="retrieval_document", output_dimensionality=768),

    )

    return response.embeddings[0].values
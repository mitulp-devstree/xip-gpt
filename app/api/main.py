import logging

from fastapi import FastAPI
from pydantic import BaseModel

from app.engine import ask_agent
from app import ingestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


class QueryRequest(BaseModel):
    query: str
    thread_id: str = "default"


@app.post("/search")
def search(req: QueryRequest):
    response_data = ask_agent(req.query, req.thread_id)
    return {
        "query": req.query,
        "answer": response_data["explanation"],
        "candidates": response_data["candidates"]
    }


@app.post("/ingest")
def ingest():
    """Trigger the vector store ingestion pipeline.
    Fetches all resumes from MongoDB, embeds them, and upserts into Qdrant.
    Returns a summary with total, indexed, and failed counts.
    """
    logger.info("[api] POST /ingest called — starting ingestion run")
    try:
        summary = ingestion.run()
        logger.info("[api] Ingestion finished: %s", summary)
        return {
            "status": "success",
            "total": summary["total"],
            "indexed": summary["indexed"],
            "failed": summary["failed"],
        }
    except Exception as exc:
        logger.error("[api] Ingestion run failed: %s", exc, exc_info=True)
        return {
            "status": "error",
            "detail": str(exc),
        }
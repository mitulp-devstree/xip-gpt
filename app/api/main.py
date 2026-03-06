import logging

from fastapi import FastAPI
from pydantic import BaseModel

from app import ingestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    thread_id: str = "default"


from fastapi import WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
from app.engine import ask_agent_stream
import os

# Serve the static UI files
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../static")), name="static")

@app.get("/")
async def get_index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "../static/index.html"))

@app.websocket("/ws/search")
async def websocket_search(websocket: WebSocket):
    await websocket.accept()
    thread_id = "default"  # Could generate a dynamic one per connection, but default is fine here
    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            query = req.get("query", "")
            if req.get("thread_id"):
                thread_id = req.get("thread_id")
            
            # Resetting context logic or passing the persistent thread
            async for chunk in ask_agent_stream(query, thread_id):
                await websocket.send_text(chunk)
                
            await websocket.send_text(json.dumps({"type": "done"}))
            # DO NOT BREAK out of the loop! We want the connection to persist for the next chat.
            
    except WebSocketDisconnect:
        logger.info(f"[api] WebSocket disconnected for thread_id {thread_id}")
    except Exception as e:
        logger.error(f"[api] WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except:
            pass # Socket might be dead already
    finally:
        try:
            await websocket.close()
        except:
            pass
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
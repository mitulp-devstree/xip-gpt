import hashlib
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from app.config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME
from app.embeddings import embed_text

logger = logging.getLogger(__name__)

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def _object_id_to_int(object_id) -> int:
    """Convert a MongoDB ObjectId (or any string) to a valid Qdrant uint64 id.
    Qdrant requires id to be an unsigned 64-bit integer or a UUID string.
    We use a stable SHA-256 hash truncated to 64 bits."""
    h = hashlib.sha256(str(object_id).encode()).hexdigest()
    return int(h[:16], 16)  # first 64 bits as unsigned int


def create_collection():
    """Create the Qdrant collection, deleting any existing one first."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        logger.info("[vector_store] Deleting existing collection '%s'", COLLECTION_NAME)
        client.delete_collection(COLLECTION_NAME)

    logger.info("[vector_store] Creating collection '%s' with size=768, COSINE distance", COLLECTION_NAME)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=768,
            distance=Distance.COSINE
        )
    )
    logger.info("[vector_store] Collection '%s' created successfully", COLLECTION_NAME)


def upsert_resume(resume_id, text, metadata):
    """Embed text and upsert a single resume point into Qdrant."""
    logger.debug("[vector_store] Embedding text for resume_id=%s", resume_id)
    vector = embed_text(text)

    point_id = _object_id_to_int(resume_id)
    logger.debug("[vector_store] Upserting point id=%s (from mongo _id=%s)", point_id, resume_id)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=metadata
            )
        ]
    )
    logger.debug("[vector_store] Upsert complete for point id=%s", point_id)


def search_vector(query, limit=10):
    """Embed a query and search the Qdrant collection."""
    logger.debug("[vector_store] Searching for query (limit=%s): %s", limit, query)
    vector = embed_text(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=limit
    )
    
    # client.query_points returns a QueryResponse, so to get points we do:
    points = results.points

    candidates = []
    seen = set()
    for pt in points:
        payload = pt.payload
        if not payload:
            continue
        
        # Create a simple unique identifier based on name, exp, and city to deduplicate
        name = payload.get("name", "Unknown")
        exp = payload.get("total_experience", "")
        city = payload.get("city", "")
        identifier = f"{name}_{exp}_{city}".strip().lower()
        
        if identifier not in seen:
            seen.add(identifier)
            candidates.append(payload)

    logger.debug("[vector_store] Search returned %s unique candidates", len(candidates))
    return candidates
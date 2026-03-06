import logging

from app.mongo import resume_collection
from app.vector_store import create_collection, upsert_resume
from app.resume_text_builder import build_resume_text

logger = logging.getLogger(__name__)


def run():
    logger.info("[ingestion] ====== Starting ingestion run ======")
    print("[ingestion] Starting ingestion run...")

    # Step 1: Create / reset the Qdrant collection
    logger.info("[ingestion] Creating Qdrant collection...")
    create_collection()
    logger.info("[ingestion] Qdrant collection ready")

    # Step 2: Fetch all non-deleted resumes from MongoDB
    resumes = list(resume_collection.find({"is_deleted": False}))
    total = len(resumes)
    logger.info("[ingestion] Found %d resumes to index", total)
    print(f"[ingestion] Found {total} resumes to index")

    indexed = 0
    failed = 0

    for i, r in enumerate(resumes, start=1):
        resume_id = r["_id"]
        logger.info("[ingestion] [%d/%d] Processing resume _id=%s", i, total, resume_id)

        try:
            # Validate extracted_data exists
            extracted = r.get("extracted_data")
            if not extracted:
                logger.warning("[ingestion] Skipping _id=%s — missing 'extracted_data'", resume_id)
                failed += 1
                continue

            # Build the text blob for embedding
            logger.debug("[ingestion] Building resume text for _id=%s", resume_id)
            text = build_resume_text(r)
            logger.debug("[ingestion] Resume text length=%d chars for _id=%s", len(text), resume_id)

            # Build metadata — keys MUST match the search filter keys in main.py
            metadata = {
                "name": extracted.get("name", ""),
                "skills": extracted.get("skills", []),
                "city": extracted.get("city", ""),
                "total_experience": extracted.get("totalExperience", 0),  # fixed key name
            }
            logger.debug("[ingestion] Metadata for _id=%s: %s", resume_id, metadata)

            # Upsert into Qdrant
            upsert_resume(resume_id, text, metadata)
            indexed += 1
            logger.info("[ingestion] [%d/%d] ✓ Indexed _id=%s", i, total, resume_id)
            print(f"[ingestion] [{i}/{total}] Indexed: {resume_id}")

        except Exception as exc:
            failed += 1
            logger.error(
                "[ingestion] [%d/%d] ✗ Failed to index _id=%s — %s: %s",
                i, total, resume_id, type(exc).__name__, exc,
                exc_info=True,
            )
            print(f"[ingestion] [{i}/{total}] ERROR indexing {resume_id}: {exc}")

    summary = {"total": total, "indexed": indexed, "failed": failed}
    logger.info("[ingestion] ====== Ingestion complete: %s ======", summary)
    print(f"[ingestion] Done. {summary}")
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    run()
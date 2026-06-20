"""
Build or rebuild the ChromaDB vector index from immigration_qa.jsonl.

Run this after:
  - Adding new rows to the CSV and converting with csv_to_jsonl.py
  - Any change to the JSONL dataset

Usage:
    python -m backend.ml.index
    python -m backend.ml.index --jsonl backend/data/immigration_qa.jsonl
"""

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Index immigration Q&A into ChromaDB")
    parser.add_argument(
        "--jsonl",
        default=str(Path(__file__).parent.parent / "data" / "immigration_qa.jsonl"),
        help="Path to JSONL file",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the collection before indexing",
    )
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl)
    if not jsonl_path.exists():
        logger.error(f"JSONL file not found: {jsonl_path}")
        return

    from .rag import RAGService, CHROMA_DIR, COLLECTION

    if args.reset:
        import chromadb
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            client.delete_collection(COLLECTION)
            logger.info(f"Deleted existing collection '{COLLECTION}'")
        except Exception:
            pass

    logger.info(f"Loading RAG service...")
    svc = RAGService()

    logger.info(f"Indexing {jsonl_path}...")
    count = svc.index_jsonl(jsonl_path)
    logger.info(f"Done — {count} documents indexed into ChromaDB at {CHROMA_DIR}")


if __name__ == "__main__":
    main()

"""
RAG (Retrieval-Augmented Generation) service using ChromaDB.

Uses ChromaDB's built-in ONNX embedding (all-MiniLM-L6-v2) — no Keras/TF needed.

Flow:
  1. index_jsonl()  — embed every row from immigration_qa.jsonl into ChromaDB (run once)
  2. retrieve()     — embed user question → find top-K similar rows → return as context
  3. build_rag_prompt() — format retrieved context + user question into a model prompt
"""

import json
import logging
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR   = Path(__file__).parent.parent / "data"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION = "immigration_qa"

_rag_service: Optional["RAGService"] = None
_lock = threading.Lock()

# Source credibility weights for re-ranking
SOURCE_BOOST = {
    "uscis.gov":         1.0,
    "travel.state.gov":  0.95,
    "attorney":          0.85,
    "community":         0.65,
    "other":             0.60,
}


class RAGService:
    def __init__(self):
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self.client    = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._embed_fn = DefaultEmbeddingFunction()   # all-MiniLM-L6-v2 via ONNX
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"RAG service ready — {self.collection.count()} docs indexed")

    # ── Indexing ─────────────────────────────────────────────────────────────

    def index_jsonl(self, jsonl_path: Path | None = None) -> int:
        path = jsonl_path or DATA_DIR / "immigration_qa.jsonl"
        records = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        if not records:
            logger.warning("No records found to index.")
            return 0

        # Embed question + partial answer for richer semantic coverage
        texts, ids, metadatas = [], [], []
        for i, r in enumerate(records):
            msg  = r.get("user_message") or r.get("input", "")
            resp = r.get("assistant_response") or r.get("output", "")
            if not msg:
                continue

            texts.append(f"{msg} {resp[:300]}")
            ids.append(f"doc_{i}")
            metadatas.append({
                "user_message":       msg,
                "assistant_response": resp,
                "visa_type":          r.get("visa_type", "Any"),
                "document_type":      r.get("document_type", "None"),
                "category":           r.get("category", "General"),
                "language":           r.get("language", "English"),
                "source":             r.get("source", "other"),
                "document_text":      r.get("document_text", "")[:500],
            })

        # Upsert — safe to re-run; same id overwrites
        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
        logger.info(f"Indexed {len(texts)} records into ChromaDB")
        return len(texts)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        visa_type: str      = "",
        document_type: str  = "",
        category: str       = "",
        language: str       = "",
        top_k: int          = 5,
    ) -> list[dict]:
        if self.collection.count() == 0:
            return []

        # Build optional metadata filters
        filters = []
        if visa_type and visa_type not in ("Any", ""):
            filters.append({"visa_type": {"$eq": visa_type}})
        if document_type and document_type not in ("None", ""):
            filters.append({"document_type": {"$eq": document_type}})
        if language and language not in ("Any", ""):
            filters.append({"language": {"$in": [language, "English"]}})

        where = {"$and": filters} if len(filters) > 1 else (filters[0] if filters else None)

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k * 2, self.collection.count()),
                where=where,
                include=["metadatas", "distances"],
            )
        except Exception:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count()),
                include=["metadatas", "distances"],
            )

        hits = []
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            similarity   = 1 - dist
            source_boost = SOURCE_BOOST.get(meta.get("source", "other"), 0.6)
            score = similarity * source_boost
            hits.append({**meta, "_score": round(score, 4)})

        hits.sort(key=lambda x: x["_score"], reverse=True)
        return hits[:top_k]

    # ── Prompt builder ────────────────────────────────────────────────────────

    def build_rag_prompt(
        self,
        user_message: str,
        retrieved: list[dict],
        document_text: str  = "",
        visa_type: str      = "Any",
        document_type: str  = "None",
        category: str       = "General",
        language: str       = "English",
    ) -> str:
        lines = ["You are an expert US immigration AI assistant."]

        meta = []
        if visa_type and visa_type != "Any":
            meta.append(f"Visa: {visa_type}")
        if document_type and document_type != "None":
            meta.append(f"Document: {document_type}")
        if category and category != "General":
            meta.append(f"Topic: {category}")
        if language and language != "English":
            meta.append(f"Reply in: {language}")
        if meta:
            lines.append(" | ".join(meta))

        if document_text:
            lines.append(f"\nUSCIS Document:\n{document_text[:800]}")

        if retrieved:
            lines.append("\nRelevant immigration knowledge:")
            for i, hit in enumerate(retrieved, 1):
                q   = hit.get("user_message", "")
                a   = hit.get("assistant_response", "")
                src = hit.get("source", "")
                lines.append(f"[{i}] Q: {q}\n    A: {a[:400]} (source: {src})")

        lines.append(f"\nUser: {user_message}")
        lines.append("Assistant:")
        return "\n".join(lines)


# ── Module-level helpers ──────────────────────────────────────────────────────

def load_rag_service() -> bool:
    global _rag_service
    with _lock:
        try:
            _rag_service = RAGService()
            return True
        except Exception as e:
            logger.error(f"Failed to load RAG service: {e}")
            return False


def get_rag_service() -> Optional[RAGService]:
    return _rag_service

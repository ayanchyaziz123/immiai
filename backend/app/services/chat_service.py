"""
Chat service — all AI answer logic lives here.

Priority chain:
  1. LoRA model + RAG context  (best quality)
  2. RAG-only retrieval         (returns best matched answer directly)
  3. Keyword search fallback    (works without any ML)
"""

import json
import logging
import re
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_JSONL_CACHE: list[dict] | None = None
_JSONL_PATH = Path(__file__).parent.parent.parent / "data" / "immigration_qa.jsonl"
_WORD_RE = re.compile(r"\b\w{3,}\b")
_JSONL_LOCK = threading.Lock()

# Simple LRU-style answer cache: skips document_text (unique per user)
_ANSWER_CACHE: dict[tuple, tuple[str, str]] = {}
_ANSWER_CACHE_LOCK = threading.Lock()


def _cache_max() -> int:
    try:
        from ..core.config import get_settings
        return get_settings().answer_cache_size
    except Exception:
        return 256


def _load_qa_cache() -> list[dict]:
    global _JSONL_CACHE
    if _JSONL_CACHE is not None:
        return _JSONL_CACHE
    with _JSONL_LOCK:
        # Re-check inside lock — another thread may have populated it
        if _JSONL_CACHE is None:
            rows: list[dict] = []
            if _JSONL_PATH.exists():
                with open(_JSONL_PATH) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            rows.append(json.loads(line))
            _JSONL_CACHE = rows
    return _JSONL_CACHE


def _keyword_search(question: str) -> str:
    qa = _load_qa_cache()
    if not qa:
        return (
            "I'm sorry, I don't have an answer for that right now. "
            "Please consult an immigration attorney for advice specific to your situation."
        )

    q_words = set(_WORD_RE.findall(question.lower()))
    best_score, best_answer = 0, None

    for item in qa:
        question_text = item.get("user_message") or item.get("input", "")
        answer_text   = item.get("assistant_response") or item.get("output", "")
        item_words = set(_WORD_RE.findall(question_text.lower()))
        score = len(q_words & item_words)
        if score > best_score:
            best_score = score
            best_answer = answer_text

    if best_score >= 2 and best_answer:
        return best_answer

    return (
        "I'm not sure about that specific question. Here are some tips:\n\n"
        "• Visit uscis.gov for official information\n"
        "• Call the USCIS Contact Center: 1-800-375-5283\n"
        "• Find free legal help at uscis.gov/avoid-scams/find-legal-services\n\n"
        "For personalised advice, always consult a licensed immigration attorney."
    )


class ChatService:
    def get_answer(
        self,
        question: str,
        language: str      = "English",
        visa_type: str     = "Any",
        document_type: str = "None",
        category: str      = "General",
        document_text: str = "",
    ) -> tuple[str, str]:
        """Returns (answer, model_version)."""
        # Cache key excludes document_text — it's user-specific and shouldn't be cached
        cache_key: tuple | None = None
        if not document_text:
            cache_key = (question.strip().lower(), language, visa_type, document_type, category)
            with _ANSWER_CACHE_LOCK:
                if cache_key in _ANSWER_CACHE:
                    logger.debug("Answer cache hit for %r", question[:60])
                    return _ANSWER_CACHE[cache_key]

        result = self._compute_answer(question, language, visa_type, document_type, category, document_text)

        if cache_key is not None:
            with _ANSWER_CACHE_LOCK:
                if len(_ANSWER_CACHE) >= _cache_max():
                    _ANSWER_CACHE.pop(next(iter(_ANSWER_CACHE)))
                _ANSWER_CACHE[cache_key] = result

        return result

    def _compute_answer(
        self,
        question: str,
        language: str,
        visa_type: str,
        document_type: str,
        category: str,
        document_text: str,
    ) -> tuple[str, str]:
        from ...ml.rag import get_rag_service
        from ...ml.inference import get_inference_service

        rag = get_rag_service()
        retrieved: list[dict] = []
        if rag:
            retrieved = rag.retrieve(
                query         = question,
                visa_type     = visa_type,
                document_type = document_type,
                language      = language,
                top_k         = 5,
            )

        svc = get_inference_service()
        if svc is not None:
            answer = svc.generate(
                question      = question,
                document_text = document_text,
                visa_type     = visa_type,
                document_type = document_type,
                category      = category,
                language      = language,
                retrieved     = retrieved,
            )
            return answer, "flan-t5-lora+rag" if retrieved else "flan-t5-lora"

        if retrieved:
            answer = retrieved[0].get("assistant_response", "")
            if answer:
                return answer, "rag-retrieval"

        return _keyword_search(question), "keyword-search"

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
from pathlib import Path

logger = logging.getLogger(__name__)

_JSONL_CACHE: list[dict] | None = None
_JSONL_PATH = Path(__file__).parent.parent.parent / "data" / "immigration_qa.jsonl"


def _load_qa_cache() -> list[dict]:
    global _JSONL_CACHE
    if _JSONL_CACHE is None:
        _JSONL_CACHE = []
        if _JSONL_PATH.exists():
            with open(_JSONL_PATH) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        _JSONL_CACHE.append(json.loads(line))
    return _JSONL_CACHE


def _keyword_search(question: str) -> str:
    qa = _load_qa_cache()
    if not qa:
        return (
            "I'm sorry, I don't have an answer for that right now. "
            "Please consult an immigration attorney for advice specific to your situation."
        )

    q_words = set(re.findall(r"\b\w{3,}\b", question.lower()))
    best_score, best_answer = 0, None

    for item in qa:
        question_text = item.get("user_message") or item.get("input", "")
        answer_text   = item.get("assistant_response") or item.get("output", "")
        item_words = set(re.findall(r"\b\w{3,}\b", question_text.lower()))
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
        """
        Returns (answer, model_version).
        model_version tells the caller which tier was used.
        """
        from ...ml.rag import get_rag_service        # backend/ml/rag.py
        from ...ml.inference import get_inference_service  # backend/ml/inference.py

        # Step 1 — RAG retrieval (runs regardless of whether model is trained)
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

        # Step 2a — LoRA model + RAG context
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
            version = "flan-t5-lora+rag" if retrieved else "flan-t5-lora"
            return answer, version

        # Step 2b — RAG-only: return best retrieved answer directly
        if retrieved:
            answer = retrieved[0].get("assistant_response", "")
            if answer:
                return answer, "rag-retrieval"

        # Step 2c — keyword search last resort
        return _keyword_search(question), "keyword-search"

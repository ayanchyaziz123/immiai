import json
import logging
import re
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_JSONL_PATH = Path(__file__).parent.parent.parent / "data" / "immigration_qa.jsonl"
_WORD_RE    = re.compile(r"\b\w{3,}\b")
_LOAD_LOCK  = threading.Lock()

# Populated once at first keyword search; never mutated afterwards.
_KW_ANSWERS: list[str]             = []   # answer text, indexed by doc position
_KW_INDEX:   dict[str, list[int]]  = {}   # word → [doc_idx, ...]
_KW_READY = False

# LRU-style answer cache (keyed without document_text — that's per-user)
_ANSWER_CACHE:      dict[tuple, tuple[str, str]] = {}
_ANSWER_CACHE_LOCK: threading.Lock               = threading.Lock()


def _cache_max() -> int:
    try:
        from ..core.config import get_settings
        return get_settings().answer_cache_size
    except Exception:
        return 256


def _build_keyword_index() -> None:
    global _KW_ANSWERS, _KW_INDEX, _KW_READY
    if _KW_READY:
        return
    with _LOAD_LOCK:
        if _KW_READY:
            return
        answers: list[str]            = []
        index:   dict[str, list[int]] = {}
        if _JSONL_PATH.exists():
            with open(_JSONL_PATH) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    r = json.loads(line)
                    q_text = r.get("user_message") or r.get("input", "")
                    a_text = r.get("assistant_response") or r.get("output", "")
                    if not q_text:
                        continue
                    pos = len(answers)
                    answers.append(a_text)
                    for word in set(_WORD_RE.findall(q_text.lower())):
                        index.setdefault(word, []).append(pos)
        _KW_ANSWERS = answers
        _KW_INDEX   = index
        _KW_READY   = True
        logger.info(f"Keyword index built: {len(answers)} docs, {len(index)} unique words")


def _default_fallback() -> str:
    return (
        "I'm not sure about that specific question. Here are some tips:\n\n"
        "• Visit uscis.gov for official information\n"
        "• Call the USCIS Contact Center: 1-800-375-5283\n"
        "• Find free legal help at uscis.gov/avoid-scams/find-legal-services\n\n"
        "For personalised advice, always consult a licensed immigration attorney."
    )


def _keyword_search(question: str) -> str:
    _build_keyword_index()
    if not _KW_INDEX:
        return (
            "I'm sorry, I don't have an answer for that right now. "
            "Please consult an immigration attorney for advice specific to your situation."
        )

    q_words = set(_WORD_RE.findall(question.lower()))
    scores:  dict[int, int] = {}
    for word in q_words:
        for idx in _KW_INDEX.get(word, []):
            scores[idx] = scores.get(idx, 0) + 1

    if not scores:
        return _default_fallback()

    best_idx   = max(scores, key=scores.__getitem__)
    best_score = scores[best_idx]

    return _KW_ANSWERS[best_idx] if best_score >= 2 else _default_fallback()


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
        """Returns (answer, model_version). Caches results when no document_text."""
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
        from ...ml.rag       import get_rag_service
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
            # Build the prompt here — avoids a second get_rag_service() call inside generate()
            if retrieved and rag:
                prompt = rag.build_rag_prompt(
                    user_message  = question,
                    retrieved     = retrieved,
                    document_text = document_text,
                    visa_type     = visa_type,
                    document_type = document_type,
                    category      = category,
                    language      = language,
                )
            else:
                from ...ml.dataset import format_prompt
                prompt = format_prompt(question, document_text, visa_type, document_type, category, language)

            answer = svc.generate_from_prompt(prompt)
            return answer, "flan-t5-lora+rag" if retrieved else "flan-t5-lora"

        if retrieved:
            answer = retrieved[0].get("assistant_response", "")
            if answer:
                return answer, "rag-retrieval"

        return _keyword_search(question), "keyword-search"

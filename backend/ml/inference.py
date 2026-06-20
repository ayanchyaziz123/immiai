import logging
import threading
from pathlib import Path

from .dataset import format_prompt as _format_prompt

logger = logging.getLogger(__name__)

MODEL_DIR   = Path(__file__).parent.parent / "models"
ADAPTER_DIR = MODEL_DIR / "lora_adapter"
BASE_MODEL  = "google/flan-t5-base"

_inference_service = None
_lock = threading.Lock()


class InferenceService:
    def __init__(self, adapter_dir: Path):
        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        from peft import PeftModel

        logger.info(f"Loading LoRA adapter from {adapter_dir}")
        self.tokenizer = AutoTokenizer.from_pretrained(str(adapter_dir))
        self.device = (
            "cuda" if torch.cuda.is_available()
            else "mps" if torch.backends.mps.is_available()
            else "cpu"
        )
        base = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL)
        self.model = PeftModel.from_pretrained(base, str(adapter_dir))
        self.model.eval()
        self.model.to(self.device)
        self._torch = torch
        logger.info(f"Model loaded on {self.device}")

    def generate(
        self,
        question: str,
        document_text: str  = "",
        visa_type: str      = "Any",
        document_type: str  = "None",
        category: str       = "General",
        language: str       = "English",
        retrieved: list     = None,
        max_new_tokens: int = 350,
        num_beams: int      = 4,
    ) -> str:
        # Use RAG prompt if retrieved context exists, otherwise plain prompt
        if retrieved:
            from .rag import get_rag_service
            rag = get_rag_service()
            if rag:
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
                prompt = _format_prompt(question, document_text, visa_type, document_type, category, language)
        else:
            prompt = _format_prompt(question, document_text, visa_type, document_type, category, language)

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=512,
            truncation=True,
        ).to(self.device)

        with self._torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                num_beams=num_beams,
                early_stopping=True,
                no_repeat_ngram_size=3,
                length_penalty=1.2,
            )

        return self.tokenizer.decode(output[0], skip_special_tokens=True)


def load_inference_service() -> bool:
    global _inference_service
    with _lock:
        if not ADAPTER_DIR.exists():
            logger.warning(f"Adapter not found at {ADAPTER_DIR}. Train the model first.")
            return False
        try:
            _inference_service = InferenceService(ADAPTER_DIR)
            return True
        except Exception as e:
            logger.error(f"Failed to load inference service: {e}")
            return False


def get_inference_service() -> InferenceService | None:
    return _inference_service


def reload_inference_service():
    global _inference_service
    with _lock:
        _inference_service = None
    return load_inference_service()

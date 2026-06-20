import json
from pathlib import Path
from datasets import Dataset, DatasetDict
from transformers import AutoTokenizer

DATA_DIR       = Path(__file__).parent.parent / "data"
MAX_INPUT_LEN  = 512
MAX_TARGET_LEN = 512
BASE_MODEL     = "google/flan-t5-base"


def format_prompt(
    user_message: str,
    document_text: str   = "",
    visa_type: str       = "Any",
    document_type: str   = "None",
    category: str        = "General",
    language: str        = "English",
) -> str:
    lines = ["You are an expert US immigration AI assistant."]

    # Context header
    meta = []
    if visa_type and visa_type != "Any":
        meta.append(f"Visa: {visa_type}")
    if document_type and document_type != "None":
        meta.append(f"Document type: {document_type}")
    if category and category != "General":
        meta.append(f"Topic: {category}")
    if language and language != "English":
        meta.append(f"Reply in: {language}")
    if meta:
        lines.append(" | ".join(meta))

    # Optional document context
    if document_text:
        lines.append(f"\nUSCIS Document:\n{document_text[:800]}")

    lines.append(f"\nUser: {user_message}")
    lines.append("Assistant:")
    return "\n".join(lines)


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_dataset(jsonl_path: Path | None = None, test_size: float = 0.2, seed: int = 42) -> DatasetDict:
    path = jsonl_path or DATA_DIR / "immigration_qa.jsonl"
    records = load_jsonl(path)

    formatted = []
    for r in records:
        # Support both old format (input/output) and new format
        user_msg = r.get("user_message") or r.get("input", "")
        response = r.get("assistant_response") or r.get("output", "")
        if not user_msg or not response:
            continue
        formatted.append({
            "input_text":  format_prompt(
                user_message  = user_msg,
                document_text = r.get("document_text", ""),
                visa_type     = r.get("visa_type", "Any"),
                document_type = r.get("document_type", "None"),
                category      = r.get("category", "General"),
                language      = r.get("language", "English"),
            ),
            "target_text": response,
        })

    ds     = Dataset.from_list(formatted)
    splits = ds.train_test_split(test_size=test_size, seed=seed)
    val_test = splits["test"].train_test_split(test_size=0.5, seed=seed)

    return DatasetDict({
        "train":      splits["train"],
        "validation": val_test["train"],
        "test":       val_test["test"],
    })


def tokenize_dataset(dataset: DatasetDict, tokenizer: AutoTokenizer) -> DatasetDict:
    def tokenize(batch):
        model_inputs = tokenizer(
            batch["input_text"],
            max_length=MAX_INPUT_LEN,
            truncation=True,
            padding="max_length",
        )
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(
                batch["target_text"],
                max_length=MAX_TARGET_LEN,
                truncation=True,
                padding="max_length",
            )
        model_inputs["labels"] = [
            [(t if t != tokenizer.pad_token_id else -100) for t in label]
            for label in labels["input_ids"]
        ]
        return model_inputs

    return dataset.map(tokenize, batched=True, remove_columns=["input_text", "target_text"])


def create_sample_dataset() -> DatasetDict:
    samples = [
        {
            "user_message": "What is a green card?",
            "assistant_response": "A green card is a permanent resident card that gives you the right to live and work in the US permanently.",
            "visa_type": "Any", "document_type": "None", "category": "Green Card", "language": "English",
        },
        {
            "user_message": "My H1B RFE says my position does not qualify as a specialty occupation. What should I do?",
            "assistant_response": "An H1B specialty occupation RFE requires a detailed response proving the position requires at least a bachelor's degree in a specific field. Gather job descriptions from similar roles, expert opinion letters, and evidence of industry standards. Respond within 87 days with a legal brief and supporting documents.",
            "visa_type": "H1B", "document_type": "RFE", "category": "RFE", "language": "English",
        },
    ]
    formatted = [{"input_text": format_prompt(**{k: v for k, v in s.items() if k != "assistant_response"}), "target_text": s["assistant_response"]} for s in samples]
    ds = Dataset.from_list(formatted)
    return DatasetDict({"train": ds, "validation": ds, "test": ds})

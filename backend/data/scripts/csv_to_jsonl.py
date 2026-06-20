"""
Convert immigration_qa.csv  →  immigration_qa.jsonl

CSV columns:
    document_text      — USCIS/RFE/notice text pasted in (or empty for general Q&A)
    user_message       — user question or chat input
    assistant_response — ideal answer the AI should generate
    visa_type          — F1 | OPT | H1B | H4 | L1 | O1 | EB1 | EB2 | EB3 |
                         B1/B2 | K1 | TN | J1 | E2 | DACA | TPS | Asylum | Any
    document_type      — RFE | Approval | Denial | Receipt | Notice | None
    category           — Travel | Work | Green Card | RFE | General
    language           — English | Bangla | Hindi | Urdu | Spanish | Chinese |
                         Arabic | French | Portuguese | Russian | Korean | Any
    verified           — yes | no  (only yes rows train the model)
    source             — uscis.gov | travel.state.gov | attorney | community | other
    date_updated       — YYYY-MM-DD

HOW TO HANDLE LAW CHANGES:
    Set old row verified=no → add new row verified=yes with today's date.
    If two verified=yes rows have the same user_message + language, the
    most recent date_updated wins automatically.

Usage:
    python csv_to_jsonl.py
    python csv_to_jsonl.py --input my_data.csv --output immigration_qa.jsonl
"""

import csv
import json
import argparse
from pathlib import Path
from datetime import date
from collections import Counter

VALID_VISA_TYPES = {
    "F1","OPT","H1B","H4","L1","L2","O1","EB1","EB2","EB3","EB5",
    "B1/B2","K1","TN","E2","J1","DACA","TPS","Asylum","Refugee","Any",
}
VALID_DOC_TYPES  = {"RFE","Approval","Denial","Receipt","Notice","None"}
VALID_CATEGORIES = {"Travel","Work","Green Card","RFE","General"}
VALID_LANGUAGES  = {
    "English","Bangla","Hindi","Urdu","Spanish","Chinese","Arabic",
    "French","Portuguese","Russian","Korean","Vietnamese","Tagalog",
    "Japanese","German","Italian","Polish","Ukrainian","Any",
}
VALID_SOURCES    = {"uscis.gov","travel.state.gov","attorney","community","other"}


def parse_date(val: str) -> date:
    try:
        return date.fromisoformat(val.strip())
    except Exception:
        return date(2000, 1, 1)


def convert(input_path: Path, output_path: Path):
    raw   = []
    skipped = 0

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {
            "document_text","user_message","assistant_response",
            "visa_type","document_type","category",
            "language","verified","source",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing columns: {missing}")

        for i, row in enumerate(reader, start=2):
            doc   = row["document_text"].strip()
            msg   = row["user_message"].strip()
            resp  = row["assistant_response"].strip()
            vtype = row["visa_type"].strip() or "Any"
            dtype = row["document_type"].strip() or "None"
            cat   = row["category"].strip() or "General"
            lang  = row["language"].strip() or "English"
            ver   = row["verified"].strip().lower()
            src   = row["source"].strip().lower() or "other"
            upd   = row.get("date_updated", "").strip() or date.today().isoformat()

            if not msg or not resp:
                skipped += 1
                continue
            if len(msg) < 3 or len(resp) < 10:
                print(f"  Row {i}: skipped (too short)")
                skipped += 1
                continue
            if ver != "yes":
                skipped += 1
                continue

            if vtype not in VALID_VISA_TYPES:
                print(f"  Row {i}: unknown visa_type '{vtype}', using 'Any'")
                vtype = "Any"
            if dtype not in VALID_DOC_TYPES:
                dtype = "None"
            if cat not in VALID_CATEGORIES:
                cat = "General"
            if lang not in VALID_LANGUAGES:
                print(f"  Row {i}: unknown language '{lang}', using 'English'")
                lang = "English"
            if src not in VALID_SOURCES:
                src = "other"

            raw.append({
                "document_text":      doc,
                "user_message":       msg,
                "assistant_response": resp,
                "visa_type":          vtype,
                "document_type":      dtype,
                "category":           cat,
                "language":           lang,
                "source":             src,
                "_date":              parse_date(upd),
            })

    # Conflict resolution: same (user_message, language) → keep most recent
    best: dict[tuple, dict] = {}
    conflicts = 0
    for row in raw:
        key = (row["user_message"].lower().strip(), row["language"])
        if key not in best or row["_date"] > best[key]["_date"]:
            if key in best:
                conflicts += 1
                print(f"  Conflict resolved: '{row['user_message'][:55]}...'")
            best[key] = row

    unique = [{k: v for k, v in r.items() if k != "_date"} for r in best.values()]

    with open(output_path, "w", encoding="utf-8") as f:
        for row in unique:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nDone!")
    print(f"  Total rows read      : {len(raw) + skipped}")
    print(f"  Skipped              : {skipped}")
    print(f"  Conflicts resolved   : {conflicts}")
    print(f"  Written to JSONL     : {len(unique)} → {output_path}")

    print(f"\n  Visa type breakdown:")
    for v, n in sorted(Counter(r["visa_type"] for r in unique).items(), key=lambda x: -x[1]):
        print(f"    {v:10s}: {n}")

    print(f"\n  Document type breakdown:")
    for d, n in sorted(Counter(r["document_type"] for r in unique).items(), key=lambda x: -x[1]):
        print(f"    {d:12s}: {n}")

    print(f"\n  Category breakdown:")
    for c, n in sorted(Counter(r["category"] for r in unique).items(), key=lambda x: -x[1]):
        bar = "█" * n
        print(f"    {c:15s}: {n:3d}  {bar}")

    print(f"\n  Language breakdown:")
    for l, n in sorted(Counter(r["language"] for r in unique).items(), key=lambda x: -x[1]):
        print(f"    {l:12s}: {n}")


if __name__ == "__main__":
    base = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default=str(base / "immigration_qa.csv"))
    parser.add_argument("--output", default=str(base / "immigration_qa.jsonl"))
    args = parser.parse_args()
    print(f"Converting: {args.input} → {args.output}\n")
    convert(Path(args.input), Path(args.output))

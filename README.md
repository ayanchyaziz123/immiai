# Immigration AI

An AI-powered US immigration assistant that answers questions about visas, green cards, asylum, citizenship, and more. Built with transfer learning (Flan-T5 + LoRA) and Retrieval-Augmented Generation (RAG), served as a web application through FastAPI.

---

## What It Does

Immigrants often struggle to find clear, reliable answers about the US immigration process. This app gives them:

- **Plain-language answers** to immigration questions in 8 languages (English, Spanish, Chinese, Hindi, Arabic, Portuguese, Bangla, Urdu)
- **Document-aware responses** — paste your RFE or denial letter and get a specific answer about your situation
- **Document checklists** — know exactly what paperwork you need for each visa type
- **Case tracking** — look up your USCIS receipt number and check processing times

---

## How It Works

### Answer Pipeline (3-tier fallback)

Every question goes through this chain. The best available tier is used automatically:

```
User question
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  Tier 1: RAG retrieval                               │
│  ChromaDB finds the 5 most similar Q&A pairs        │
│  from the training dataset using semantic search     │
└────────────────────┬────────────────────────────────┘
                     │ top-5 results
                     ▼
┌─────────────────────────────────────────────────────┐
│  Tier 1a: LoRA model + RAG context (best quality)   │
│  Flan-T5 reads the question + retrieved context     │
│  and generates a fluent, accurate answer            │
│  (only available after training notebooks are run)  │
├─────────────────────────────────────────────────────┤
│  Tier 1b: RAG-only (no model trained yet)           │
│  Returns the best matched answer directly from      │
│  the dataset — works immediately on first run       │
├─────────────────────────────────────────────────────┤
│  Tier 2: Keyword search (last resort)               │
│  Simple word overlap search over the JSONL dataset  │
└─────────────────────────────────────────────────────┘
```

The status badge in the top-right of every page shows which tier is active.

### ML Architecture

| Component | Technology | Role |
|---|---|---|
| Base model | `google/flan-t5-base` (250M params) | Seq2Seq text generation |
| Fine-tuning | PEFT LoRA (r=16, target q/v attention) | Adapts the model to immigration domain without full retraining |
| Embeddings | ChromaDB built-in ONNX (all-MiniLM-L6-v2, 384-dim) | Semantic search over Q&A dataset |
| Vector store | ChromaDB (local persistent) | Stores and retrieves embedded Q&A pairs |
| Training tracking | MLflow | Logs loss, ROUGE scores, training config |
| Export | Hugging Face Optimum → ONNX | Optional faster inference |

### RAG (Retrieval-Augmented Generation)

Instead of the model memorising all answers in its weights, RAG retrieves relevant knowledge at query time:

1. Every Q&A pair in the dataset is embedded (question + partial answer) and stored in ChromaDB
2. When a user asks a question, it is embedded and compared against all stored vectors using cosine similarity
3. The top-5 most relevant Q&A pairs are retrieved
4. Retrieved answers are re-ranked using **source credibility** (`uscis.gov` scores higher than `community`)
5. The retrieved context is injected into the prompt before the model generates a final answer

This means the model always has current, relevant context rather than relying purely on what it learned during training.

---

## Project Structure

```
immigration AI/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory + startup
│   │   ├── core/
│   │   │   ├── config.py            # All settings (pydantic-settings, .env support)
│   │   │   ├── database.py          # Async SQLAlchemy engine
│   │   │   ├── dependencies.py      # FastAPI Depends() (get_db)
│   │   │   └── exceptions.py        # Custom error classes + handlers
│   │   ├── api/v1/
│   │   │   ├── router.py            # Aggregates all API routers under /api/v1
│   │   │   └── endpoints/
│   │   │       ├── chat.py          # POST /api/v1/chat/  (thin HTTP handler)
│   │   │       ├── checklist.py     # POST /api/v1/checklist/
│   │   │       ├── training.py      # POST /api/v1/training/start
│   │   │       └── web.py           # GET / /checklist /tracker (HTML pages)
│   │   ├── models/
│   │   │   └── conversation.py      # SQLAlchemy: Conversation + Message tables
│   │   ├── schemas/
│   │   │   ├── chat.py              # ChatRequest, ChatResponse, ConversationOut
│   │   │   ├── checklist.py         # ChecklistRequest, ChecklistResponse
│   │   │   └── training.py          # TrainingJobRequest, TrainingJobResponse
│   │   ├── services/
│   │   │   ├── chat_service.py      # All AI answer logic (RAG + model + fallback)
│   │   │   ├── checklist_service.py # Document checklist data + lookup
│   │   │   └── training_service.py  # Celery job queue management
│   │   ├── repositories/
│   │   │   └── conversation_repository.py  # All database queries
│   │   ├── static/
│   │   │   ├── css/app.css          # All styles
│   │   │   └── js/                  # chat.js, checklist.js, tracker.js
│   │   └── templates/               # Jinja2 HTML templates
│   │       ├── base.html            # Navbar, status badge, shared layout
│   │       ├── chat.html            # AI assistant page
│   │       ├── checklist.html       # Document checklist page
│   │       └── tracker.html         # Case tracker page
│   ├── ml/
│   │   ├── dataset.py               # format_prompt() + build_dataset()
│   │   ├── inference.py             # InferenceService (lazy-loads LoRA model)
│   │   ├── rag.py                   # RAGService (ChromaDB index + retrieval)
│   │   ├── train.py                 # Training loop (called by Celery worker)
│   │   └── indexer.py               # CLI to build/rebuild the ChromaDB index
│   ├── data/
│   │   ├── immigration_qa.csv       # Source of truth (10-column training data)
│   │   ├── immigration_qa.jsonl     # Converted from CSV, used by RAG + training
│   │   └── scripts/
│   │       └── csv_to_jsonl.py      # CSV → JSONL converter with validation
│   ├── workers/
│   │   ├── celery_app.py            # Celery configuration
│   │   └── tasks.py                 # finetune_model task
│   ├── tests/
│   │   ├── conftest.py              # Async test client + in-memory SQLite
│   │   ├── api/test_chat.py
│   │   └── services/test_checklist_service.py
│   ├── requirements.txt
│   └── requirements-dev.txt
├── notebooks/
│   ├── 01_data_prep.ipynb           # Load CSV → format prompts → build RAG index
│   ├── 02_finetune_lora.ipynb       # Fine-tune Flan-T5 with LoRA
│   ├── 03_evaluate.ipynb            # ROUGE + BLEU evaluation
│   └── 04_export_onnx.ipynb         # Export to ONNX for faster inference
└── docker-compose.yml               # PostgreSQL + Redis + MLflow + API + Worker
```

---

## Training Data Format

The dataset lives in `backend/data/immigration_qa.csv`. Each row has 10 columns:

| Column | Description | Example |
|---|---|---|
| `document_text` | Pasted USCIS document text (optional) | `"We are requesting evidence of..."` |
| `user_message` | The immigration question | `"What is the H-1B visa?"` |
| `assistant_response` | The correct answer | `"The H-1B is a non-immigrant visa..."` |
| `visa_type` | Visa category | `H-1B`, `F-1`, `Green Card`, `Asylum`, `Any` |
| `document_type` | Type of USCIS document | `RFE`, `Denial`, `Approval Notice`, `None` |
| `category` | Topic area | `Employment`, `Family`, `Travel`, `General` |
| `language` | Language of the answer | `English`, `Spanish`, `Bangla`, etc. |
| `verified` | Is this row accurate? | `yes` / `no` |
| `source` | Where the information came from | `uscis.gov`, `attorney`, `community` |
| `date_updated` | When this row was last verified | `2026-06-20` (auto-fills if blank) |

**Rules:**
- Only `verified=yes` rows are used for training or RAG indexing
- If the same question exists twice, the row with the newer `date_updated` wins
- `date_updated` auto-fills to today's date if you leave it blank

---

## Getting Started

### Prerequisites

- Python 3.11+ (Anaconda recommended)
- macOS / Linux (Windows with WSL)

### 1. Install dependencies

```bash
# Using Anaconda (recommended — avoids venv/conda conflicts)
/opt/anaconda3/bin/pip install -r backend/requirements.txt

# Or with a standard venv
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Convert the CSV to JSONL

```bash
python -m backend.data.csv_to_jsonl
```

This validates the CSV, resolves conflicts, and writes `backend/data/immigration_qa.jsonl`.

### 3. Start the server

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

On first start, the server automatically:
- Creates the SQLite database (`immigration_ai.db`)
- Downloads the ONNX embedding model (~80 MB, one time only)
- Indexes all 97 Q&A rows into ChromaDB

Open **http://localhost:8000** in your browser.

---

## Training the Model (Optional but Recommended)

The app works immediately via RAG without training. Training makes answers more fluent and context-aware.

### Option A — Jupyter Notebooks (recommended for first time)

```bash
pip install jupyter
jupyter notebook notebooks/
```

Run in order:
1. **01_data_prep.ipynb** — loads the CSV, formats prompts, splits train/val/test, builds RAG index
2. **02_finetune_lora.ipynb** — fine-tunes Flan-T5 with LoRA (takes 20–60 min depending on hardware)
3. **03_evaluate.ipynb** — measures ROUGE and BLEU scores on the test set
4. **04_export_onnx.ipynb** — exports to ONNX for faster CPU inference

### Option B — Via the Web UI

Start the server and the worker, then use the training trigger in the API:

```bash
# Terminal 1 — start Redis (required for training jobs)
docker run -p 6379:6379 redis:7-alpine

# Terminal 2 — start the Celery worker
/opt/anaconda3/bin/python -m celery -A backend.workers.celery_app.celery_app worker --loglevel=info

# Terminal 3 — start the API
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Then POST to `http://localhost:8000/api/v1/training/start`:
```json
{ "epochs": 5, "batch_size": 4, "learning_rate": 0.0003, "lora_r": 16 }
```

After training completes, the model reloads automatically.

---

## Adding New Training Data

1. Open `backend/data/immigration_qa.csv` in any spreadsheet app or text editor
2. Add rows — only these columns are required, everything else is optional:

```
user_message, assistant_response, visa_type, category, language, verified, source
```

3. Set `verified=yes` on new rows (leave `date_updated` blank — it auto-fills)
4. Run the converter:

```bash
python -m backend.data.csv_to_jsonl
```

5. Rebuild the RAG index:

```bash
python -m backend.ml.indexer --reset
```

6. Restart the server — new knowledge is live immediately via RAG (no retraining needed)

> **Tip:** To update an outdated answer, add a new row with the corrected answer and today's date. Set `verified=no` on the old row. The converter will automatically use the newer row.

---

## Web Pages

| URL | Description |
|---|---|
| `http://localhost:8000` | AI chat assistant |
| `http://localhost:8000/checklist` | Document checklist by visa type |
| `http://localhost:8000/tracker` | USCIS case status + processing times |
| `http://localhost:8000/docs` | Interactive API documentation (Swagger) |
| `http://localhost:8000/redoc` | API reference (ReDoc) |
| `http://localhost:8000/health` | JSON health check (model_ready, rag_ready, rag_docs) |

---

## API Reference

### POST /api/v1/chat/

Ask an immigration question.

**Request:**
```json
{
  "question": "What documents do I need for an H-1B?",
  "language": "English",
  "visa_type": "H-1B",
  "document_type": "None",
  "category": "General",
  "document_text": "(optional) paste your RFE or denial text here"
}
```

**Response:**
```json
{
  "answer": "For an H-1B petition you will need...",
  "conversation_id": "uuid",
  "message_id": "uuid",
  "model_version": "flan-t5-lora+rag",
  "processing_time_ms": 320
}
```

`model_version` tells you which tier answered:

| Value | Meaning |
|---|---|
| `flan-t5-lora+rag` | Fine-tuned model + RAG context (best) |
| `flan-t5-lora` | Fine-tuned model, no RAG match |
| `rag-retrieval` | Direct RAG match, model not trained yet |
| `keyword-search` | Keyword fallback, no RAG index |

### POST /api/v1/checklist/

Get a document checklist for a visa type.

```json
{ "visa_type": "h-1b" }
```

### GET /api/v1/chat/conversations

List recent conversations.

### GET /health

```json
{
  "status": "ok",
  "model_ready": false,
  "rag_ready": true,
  "rag_docs": 97,
  "model": "google/flan-t5-base",
  "version": "1.0.0"
}
```

---

## Running Tests

```bash
cd backend
/opt/anaconda3/bin/python -m pytest tests/ -v
```

---

## Docker (Production)

Runs PostgreSQL + Redis + MLflow + API + Celery worker together:

```bash
docker-compose up --build
```

Services:
| Service | Port | Description |
|---|---|---|
| API | 8000 | FastAPI web app |
| PostgreSQL | 5432 | Production database |
| Redis | 6379 | Celery broker |
| MLflow | 5000 | Training experiment tracker |

---

## Environment Variables

Create a `.env` file in the project root to override defaults:

```env
DATABASE_URL=sqlite+aiosqlite:///./immigration_ai.db
REDIS_URL=redis://localhost:6379/0
BASE_MODEL=google/flan-t5-base
ADAPTER_PATH=backend/models/lora_adapter
DEBUG=false
MLFLOW_TRACKING_URI=http://localhost:5000
MAX_NEW_TOKENS=350
NUM_BEAMS=4
```

---

## Supported Languages

English · Spanish · Chinese · Hindi · Arabic · Portuguese · Bangla · Urdu

Add more by adding rows in the CSV with `language=<language name>`.

---

## Disclaimer

This application provides general information only. Immigration law is complex and changes frequently. Always verify information at [uscis.gov](https://www.uscis.gov) and consult a licensed immigration attorney for advice specific to your situation. Free legal help is available at [uscis.gov/avoid-scams/find-legal-services](https://www.uscis.gov/avoid-scams/find-legal-services).

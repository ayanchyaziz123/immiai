import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.v1.router import api_v1_router
from .core.config import get_settings
from .core.database import init_db
from .core.exceptions import register_exception_handlers

_APP_DIR = Path(__file__).parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────
    await init_db()
    logger.info("Database ready")

    _load_ml_services()

    yield
    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("Shutting down Immigration AI API")


def _load_ml_services() -> None:
    from ..ml.inference import load_inference_service
    from ..ml.rag import get_rag_service, load_rag_service

    load_inference_service()

    if load_rag_service():
        rag = get_rag_service()
        if rag and rag.collection.count() == 0:
            jsonl = Path("backend/data/immigration_qa.jsonl")
            if jsonl.exists():
                count = rag.index_jsonl(jsonl)
                logger.info(f"Auto-indexed {count} documents into ChromaDB")
    else:
        logger.warning("RAG service unavailable — falling back to keyword search")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI-powered US immigration assistant. "
            "Uses Flan-T5 + LoRA fine-tuning and RAG (ChromaDB) for accurate, "
            "context-aware answers in multiple languages."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # Static files (CSS, JS)
    app.mount("/static", StaticFiles(directory=str(_APP_DIR / "static")), name="static")

    # Web pages (must come before API router so / is the chat page)
    from .api.v1.endpoints.web import router as web_router
    app.include_router(web_router)

    # JSON API
    app.include_router(api_v1_router)
    _register_health(app)

    return app


def _register_health(app: FastAPI) -> None:
    @app.get("/health", tags=["health"])
    async def health():
        from ..ml.inference import get_inference_service
        from ..ml.rag import get_rag_service

        rag = get_rag_service()
        rag_count = rag.collection.count() if rag else 0

        return {
            "status":      "ok",
            "model_ready": get_inference_service() is not None,
            "rag_ready":   rag is not None and rag_count > 0,
            "rag_docs":    rag_count,
            "model":       settings.base_model,
            "version":     settings.app_version,
        }


app = create_app()

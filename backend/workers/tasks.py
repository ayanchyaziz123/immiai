import logging
from .celery_app import celery_app
from ..ml.train import TrainConfig, run_training
from ..ml.inference import reload_inference_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="finetune_model")
def finetune_model(self, job_id: str, config_dict: dict):
    def progress(pct: int, message: str):
        self.update_state(
            state="PROGRESS",
            meta={"job_id": job_id, "percent": pct, "message": message},
        )
        logger.info(f"[{job_id}] {pct}% — {message}")

    try:
        config = TrainConfig(
            epochs=config_dict.get("epochs", 5),
            batch_size=config_dict.get("batch_size", 4),
            learning_rate=config_dict.get("learning_rate", 3e-4),
            lora_r=config_dict.get("lora_r", 16),
        )

        progress(0, "Starting training job")
        results = run_training(config, progress_callback=progress)

        logger.info(f"[{job_id}] Training complete. Reloading inference service.")
        reload_inference_service()

        return {
            "job_id": job_id,
            "status": "success",
            **results,
        }
    except Exception as e:
        logger.exception(f"[{job_id}] Training failed: {e}")
        self.update_state(
            state="FAILURE",
            meta={"job_id": job_id, "error": str(e)},
        )
        raise

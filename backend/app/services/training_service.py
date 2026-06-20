import uuid
import logging

from ..schemas.training import TrainingJobRequest, TrainingJobResponse

logger = logging.getLogger(__name__)


class TrainingService:
    def start_job(self, request: TrainingJobRequest) -> TrainingJobResponse:
        from ...workers.tasks import finetune_model

        job_id = str(uuid.uuid4())
        config = {
            "epochs":        request.epochs,
            "batch_size":    request.batch_size,
            "learning_rate": request.learning_rate,
            "lora_r":        request.lora_r,
        }
        finetune_model.apply_async(args=[job_id, config], task_id=job_id)
        logger.info(f"Training job {job_id} queued with config: {config}")

        return TrainingJobResponse(
            job_id=job_id,
            status="queued",
            message=f"Training job {job_id} queued. Check status at /api/v1/training/status/{job_id}",
        )

    def get_status(self, job_id: str) -> dict:
        from celery.result import AsyncResult
        from ...workers.celery_app import celery_app

        result = AsyncResult(job_id, app=celery_app)
        return {
            "job_id": job_id,
            "status": result.state,
            "info":   result.info if result.info else {},
        }

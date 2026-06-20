import asyncio

from fastapi import APIRouter, HTTPException

from ....schemas.training import TrainingJobRequest, TrainingJobResponse
from ....services.training_service import TrainingService

router = APIRouter(prefix="/training", tags=["training"])
_training_service = TrainingService()


@router.post("/start", response_model=TrainingJobResponse)
async def start_training(request: TrainingJobRequest):
    try:
        # apply_async contacts Redis synchronously — offload so the event loop stays free
        return await asyncio.to_thread(_training_service.start_job, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
async def get_training_status(job_id: str):
    try:
        # AsyncResult.state also does a Redis lookup
        return await asyncio.to_thread(_training_service.get_status, job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

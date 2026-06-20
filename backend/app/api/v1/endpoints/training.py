from fastapi import APIRouter, HTTPException

from ....schemas.training import TrainingJobRequest, TrainingJobResponse
from ....services.training_service import TrainingService

router = APIRouter(prefix="/training", tags=["training"])
_training_service = TrainingService()


@router.post("/start", response_model=TrainingJobResponse)
async def start_training(request: TrainingJobRequest):
    try:
        return _training_service.start_job(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
async def get_training_status(job_id: str):
    try:
        return _training_service.get_status(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

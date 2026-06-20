from pydantic import BaseModel, Field


class TrainingJobRequest(BaseModel):
    epochs: int = Field(default=5, ge=1, le=20)
    batch_size: int = Field(default=4, ge=1, le=32)
    learning_rate: float = Field(default=3e-4, gt=0)
    lora_r: int = Field(default=16, ge=4, le=64)


class TrainingJobResponse(BaseModel):
    job_id: str
    status: str
    message: str

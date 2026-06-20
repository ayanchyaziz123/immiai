from typing import Optional
from pydantic import BaseModel, Field


class ChecklistRequest(BaseModel):
    visa_type: str = Field(..., description="e.g. 'marriage green card', 'H-1B', 'asylum'")
    country_of_birth: Optional[str] = None


class ChecklistItem(BaseModel):
    item: str
    required: bool
    notes: Optional[str] = None


class ChecklistResponse(BaseModel):
    visa_type: str
    items: list[ChecklistItem]

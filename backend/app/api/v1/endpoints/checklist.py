from fastapi import APIRouter

from ....schemas.checklist import ChecklistRequest, ChecklistResponse
from ....services.checklist_service import ChecklistService

router = APIRouter(prefix="/checklist", tags=["checklist"])
_checklist_service = ChecklistService()


@router.post("/", response_model=ChecklistResponse)
async def get_checklist(request: ChecklistRequest):
    return _checklist_service.get_checklist(request.visa_type)


@router.get("/types")
async def list_checklist_types():
    return {"available_types": _checklist_service.list_types()}

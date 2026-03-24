from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core.state import AppState, get_state
from backend.schemas.admin import (
    AdminClip,
    AddToQueueRequest,
    RemoveFromQueueRequest,
    QueueStatusResponse,
    ProcessRequest,
    ProcessStatusResponse,
)

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/admin/queue", response_model=QueueStatusResponse)
async def add_to_admin_queue(
    request: AddToQueueRequest,
    state: AppState = Depends(get_state),
) -> QueueStatusResponse:
    result = await state.add_to_queue(request.clip_id)
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail="Clip not found")
    return QueueStatusResponse(**result)


@router.post("/admin/remove", response_model=QueueStatusResponse)
async def remove_from_admin_queue(
    request: RemoveFromQueueRequest,
    state: AppState = Depends(get_state),
) -> QueueStatusResponse:
    result = await state.remove_from_queue(request.clip_id)
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail="Clip not found in queue")
    return QueueStatusResponse(**result)


@router.get("/accepted", response_model=List[AdminClip])
async def get_accepted_clips(
    state: AppState = Depends(get_state),
) -> List[AdminClip]:
    clips = await state.get_accepted_clips()
    return clips


@router.post("/process", response_model=ProcessStatusResponse)
async def process_clips(
    request: ProcessRequest,
    state: AppState = Depends(get_state),
) -> ProcessStatusResponse:
    if not request.clip_ids:
        return ProcessStatusResponse(status="empty")

    return ProcessStatusResponse(status="processing")

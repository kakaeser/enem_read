from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.dependencies import get_exam_manager_service
from backend.core.exceptions import NotFoundException
from backend.schemas.exam import ExamCreate, ExamResponse, ExamUpdate
from backend.services.exam_manager_service import ExamManagerService

router = APIRouter(prefix="/exams", tags=["exams"])


@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    exam_data: ExamCreate,
    service: ExamManagerService = Depends(get_exam_manager_service),
):
    """Create a new exam session."""
    try:
        return await service.create_exam(exam_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/", response_model=List[ExamResponse])
async def list_exams(
    status_filter: Optional[str] = Query(None, alias="status"),
    name: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ExamManagerService = Depends(get_exam_manager_service),
):
    """List all exams with optional filtering."""
    try:
        return await service.list_exams(
            status=status_filter, name=name, skip=skip, limit=limit
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: int,
    service: ExamManagerService = Depends(get_exam_manager_service),
):
    """Get exam details by ID."""
    try:
        return await service.get_exam(exam_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.patch("/{exam_id}", response_model=ExamResponse)
async def update_exam(
    exam_id: int,
    exam_data: ExamUpdate,
    service: ExamManagerService = Depends(get_exam_manager_service),
):
    """Update exam configuration fields."""
    try:
        return await service.update_exam(exam_id, exam_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    exam_id: int,
    service: ExamManagerService = Depends(get_exam_manager_service),
):
    """Delete an exam and all associated data."""
    try:
        deleted = await service.delete_exam(exam_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exam with id {exam_id} not found",
            )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post("/{exam_id}/finish", response_model=ExamResponse)
async def finish_exam(
    exam_id: int,
    service: ExamManagerService = Depends(get_exam_manager_service),
):
    """
    Lock an exam: set status='completed' and ended_at=utcnow() server-side.
    Returns 409 if already completed, 404 if not found.
    Requirements: 17.1, 17.2, 17.3, 17.4
    """
    try:
        exam_response = await service.get_exam(exam_id)
    except (ValueError, NotFoundException) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if exam_response.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Exam {exam_id} is already completed",
        )

    update = ExamUpdate(status="completed", ended_at=datetime.utcnow())
    try:
        return await service.update_exam(exam_id, update)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

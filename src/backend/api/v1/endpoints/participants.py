from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from backend.api.dependencies import (
    get_exam_manager_service,
    get_participant_repository,
)
from backend.core.exceptions import NotFoundException
from backend.repositories.implemations.async_participant_repo import AsyncParticipantRepository
from backend.schemas.participante import ParticipantAddRequest, ParticipantCreate, ParticipantResponse, ParticipantUpdate
from backend.services.exam_manager_service import ExamManagerService

# Routes nested under /exams for participant collection operations
exam_participants_router = APIRouter(prefix="/exams", tags=["participants"])

# Routes for direct participant access by ID
participants_router = APIRouter(prefix="/participants", tags=["participants"])


@exam_participants_router.post(
    "/{exam_id}/participants",
    response_model=ParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_participant(
    exam_id: int,
    participant_data: ParticipantAddRequest,
    service: ExamManagerService = Depends(get_exam_manager_service),
    participant_repo: AsyncParticipantRepository = Depends(get_participant_repository),
):
    """
    Manually add a participant to an exam.
    Allows duplicate names within the same exam but returns a warning header.
    Requirements: 17.1, 17.2, 17.3, 17.4, 17.5
    """
    # Check for duplicate name in the same exam (warn but allow - Req 17.8)
    existing = await participant_repo.get_by_exam_and_name(exam_id, participant_data.nome.strip())
    duplicate_warning = existing is not None

    # Build a ParticipantCreate with the correct exam_id
    data = ParticipantCreate(nome=participant_data.nome, exam_id=exam_id)

    try:
        result = await service.add_participant_to_exam(exam_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )

    if duplicate_warning:
        # Return 201 with a warning header per Req 17.8
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=result.model_dump(),
            headers={"X-Warning": f"Duplicate name '{participant_data.nome}' in exam {exam_id}"},
        )

    return result


@exam_participants_router.get(
    "/{exam_id}/participants",
    response_model=List[ParticipantResponse],
)
async def list_participants(
    exam_id: int,
    service: ExamManagerService = Depends(get_exam_manager_service),
    participant_repo: AsyncParticipantRepository = Depends(get_participant_repository),
):
    """
    List all participants for a given exam.
    Requirements: 17.6, 17.7
    """
    # Verify exam exists
    try:
        await service.get_exam(exam_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)

    try:
        participants = await participant_repo.get_by_exam_id(exam_id)
        return [ParticipantResponse.model_validate(p) for p in participants]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@participants_router.patch(
    "/{participant_id}",
    response_model=ParticipantResponse,
)
async def update_participant(
    participant_id: int,
    update_data: ParticipantUpdate,
    participant_repo: AsyncParticipantRepository = Depends(get_participant_repository),
):
    """
    Update participant fields: nome, presente, essay_points.
    essay_points must be >= 0 (validated by schema).
    Requirements: 18.3, 18.4, 18.5
    """
    participant = await participant_repo.get_by_id(participant_id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant with id {participant_id} not found",
        )

    fields = update_data.model_dump(exclude_none=True)
    for field, value in fields.items():
        setattr(participant, field, value)

    try:
        updated = await participant_repo.update(participant)
        return ParticipantResponse.model_validate(updated)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@participants_router.delete(
    "/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_participant(
    participant_id: int,
    participant_repo: AsyncParticipantRepository = Depends(get_participant_repository),
):
    """
    Delete a participant by ID.
    Requirements: 18.3
    """
    participant = await participant_repo.get_by_id(participant_id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant with id {participant_id} not found",
        )

    try:
        await participant_repo.delete(participant_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )

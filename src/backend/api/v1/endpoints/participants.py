from typing import List, Optional
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import JSONResponse

from backend.api.dependencies import (
    get_exam_manager_service,
    get_participant_repository,
    get_question_repository,
    get_response_repository,
)
from backend.core.exceptions import NotFoundException
from backend.repositories.implemations.async_participant_repo import AsyncParticipantRepository
from backend.repositories.implemations.async_question_repo import AsyncQuestionRepository
from backend.repositories.implemations.async_response_repo import AsyncResponseRepository
from backend.schemas.participante import ParticipantAddRequest, ParticipantCreate, ParticipantResponse, ParticipantUpdate
from backend.schemas.scoring import QuestionResponseDetail
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
    presente: Optional[bool] = Query(None),
    service: ExamManagerService = Depends(get_exam_manager_service),
    participant_repo: AsyncParticipantRepository = Depends(get_participant_repository),
):
    """
    List participants for a given exam.
    Optional ?presente=true/false filter.
    Requirements: 14.1, 14.2, 14.3
    """
    try:
        await service.get_exam(exam_id)
    except (ValueError, NotFoundException) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    try:
        if presente is None:
            participants = await participant_repo.get_by_exam_id(exam_id)
        elif presente:
            participants = await participant_repo.get_present_by_exam_id(exam_id)
        else:
            participants = await participant_repo.get_absent_by_exam_id(exam_id)
        return [ParticipantResponse.model_validate(p) for p in participants]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


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


# ---------------------------------------------------------------------------
# Bulk import — Task 3.2  (Requirements 15.1–15.7)
# ---------------------------------------------------------------------------

@exam_participants_router.post(
    "/{exam_id}/participants/import",
    status_code=status.HTTP_200_OK,
)
async def import_participants(
    exam_id: int,
    file: UploadFile = File(...),
    service: ExamManagerService = Depends(get_exam_manager_service),
    participant_repo: AsyncParticipantRepository = Depends(get_participant_repository),
):
    """
    Bulk-import participants from a CSV or Excel file.
    CSV: column 'nome' or 'Nome'. Excel: column 'Nome'.
    Returns ImportResult: {imported, skipped, errors}.
    Requirements: 15.1–15.7
    """
    try:
        await service.get_exam(exam_id)
    except (ValueError, NotFoundException) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    filename = file.filename or ""
    content = await file.read()

    if filename.endswith(".csv"):
        try:
            df = pd.read_csv(BytesIO(content))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not parse CSV: {exc}")
        col = next((c for c in df.columns if c.strip().lower() == "nome"), None)
        if col is None:
            raise HTTPException(status_code=422, detail="CSV must contain a 'nome' or 'Nome' column")
    elif filename.endswith((".xlsx", ".xls")):
        try:
            df = pd.read_excel(BytesIO(content))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not parse Excel file: {exc}")
        col = next((c for c in df.columns if c.strip().lower() == "nome"), None)
        if col is None:
            raise HTTPException(status_code=422, detail="Excel file must contain a 'Nome' column")
    else:
        raise HTTPException(status_code=422, detail="Unsupported file format. Use CSV or Excel (.xlsx/.xls)")

    from backend.entities.participante import Participante

    imported = 0
    skipped = 0
    errors: list[str] = []

    for raw in df[col]:
        if pd.isna(raw) or str(raw).strip() == "":
            skipped += 1
            continue
        nome = str(raw).strip()
        existing = await participant_repo.get_by_exam_and_name(exam_id, nome)
        if existing is not None:
            skipped += 1
            continue
        try:
            p = Participante(exam_id=exam_id, nome=nome, presente=False, essay_points=0.0)
            await participant_repo.create(p)
            imported += 1
        except Exception as exc:
            errors.append(f"Row '{nome}': {exc}")

    return {"imported": imported, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# Per-participant response detail — Task 4.1  (Requirements 16.1–16.4)
# ---------------------------------------------------------------------------

@exam_participants_router.get(
    "/{exam_id}/participants/{participant_id}/responses",
    response_model=List[QuestionResponseDetail],
)
async def get_participant_responses(
    exam_id: int,
    participant_id: int,
    service: ExamManagerService = Depends(get_exam_manager_service),
    participant_repo: AsyncParticipantRepository = Depends(get_participant_repository),
    question_repo: AsyncQuestionRepository = Depends(get_question_repository),
    response_repo: AsyncResponseRepository = Depends(get_response_repository),
):
    """
    Per-question answer breakdown for a single participant.
    Ordered by question_number ascending.
    Requirements: 16.1–16.4
    """
    try:
        await service.get_exam(exam_id)
    except (ValueError, NotFoundException) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    participant = await participant_repo.get_by_id(participant_id)
    if participant is None or participant.exam_id != exam_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found in exam {exam_id}",
        )

    questions = await question_repo.get_by_exam_id(exam_id)
    responses = await response_repo.get_by_participant_and_exam(participant_id, exam_id)
    response_map = {r.quest_id: r for r in responses}

    result: List[QuestionResponseDetail] = []
    for q in sorted(questions, key=lambda x: x.numero):
        resp = response_map.get(q.id)
        if q.question_correct_answer is None:
            correct_answer = None
            correct = None
        else:
            correct_answer = q.question_correct_answer
            correct = (resp.marked_answer == correct_answer) if resp and resp.marked_answer else False

        result.append(QuestionResponseDetail(
            question_number=q.numero,
            correct_answer=correct_answer,
            marked_answer=resp.marked_answer if resp else None,
            correct=correct,
            peso=q.peso,
        ))

    return result

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from typing import Dict

from backend.api.dependencies import (
    get_exam_repository,
    get_ocr_service,
    get_question_repository,
    get_response_repository,
)
from backend.core.exceptions import NotFoundException, OCRProcessingException
from backend.entities.questao import Questao
from backend.entities.resposta import Resposta
from backend.repositories.implemations.async_exam_repo import AsyncExamRepository
from backend.repositories.implemations.async_question_repo import AsyncQuestionRepository
from backend.repositories.implemations.async_response_repo import AsyncResponseRepository
from backend.schemas.ocr import AnswerKeyResult, AnswerSheetResult
from backend.services.ocr.ocr_service import OCRService
from pydantic import BaseModel

router = APIRouter(prefix="/exams", tags=["ocr"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


async def _validate_image(file: UploadFile) -> bytes:
    """Read file bytes and validate content type and size."""
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Only JPEG and PNG are allowed.",
        )

    content = await file.read()

    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 5 MB limit.",
        )

    return content


@router.post(
    "/{exam_id}/ocr/answer-key",
    response_model=AnswerKeyResult,
    summary="Upload and process an answer key image via OCR",
)
async def process_answer_key(
    exam_id: int,
    file: UploadFile = File(...),
    exam_repo: AsyncExamRepository = Depends(get_exam_repository),
    question_repo: AsyncQuestionRepository = Depends(get_question_repository),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Upload a JPEG or PNG image of the answer key for the given exam.
    Extracts question-answer pairs via OCR and persists them as Question records.

    Requirements: 5.1, 5.5
    """
    exam = await exam_repo.get_by_id(exam_id)
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with id {exam_id} not found",
        )

    image_bytes = await _validate_image(file)

    try:
        result = await ocr_service.process_answer_key(
            image_file=image_bytes,
            exam_id=exam_id,
            exam_questions_numbers=exam.questions_numbers,
            question_repo=question_repo,
        )
    except OCRProcessingException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message,
        )
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.error_message or "OCR could not extract any answers from the image.",
        )

    return result


@router.post(
    "/{exam_id}/ocr/answer-sheet",
    response_model=AnswerSheetResult,
    summary="Upload and process a participant answer sheet image via OCR",
)
async def process_answer_sheet(
    exam_id: int,
    participant_id: int = Query(..., description="ID of the participant whose sheet is being processed"),
    file: UploadFile = File(...),
    exam_repo: AsyncExamRepository = Depends(get_exam_repository),
    question_repo: AsyncQuestionRepository = Depends(get_question_repository),
    response_repo: AsyncResponseRepository = Depends(get_response_repository),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Upload a JPEG or PNG image of a participant's answer sheet for the given exam.
    Extracts marked answers via OCR and persists them as Response records.

    Requirements: 6.1, 6.2, 6.6
    """
    exam = await exam_repo.get_by_id(exam_id)
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam with id {exam_id} not found",
        )

    image_bytes = await _validate_image(file)

    try:
        result = await ocr_service.process_answer_sheet(
            image_file=image_bytes,
            participant_id=participant_id,
            exam_id=exam_id,
            question_repo=question_repo,
            response_repo=response_repo,
        )
    except OCRProcessingException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message,
        )
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.error_message or "OCR could not extract any answers from the image.",
        )

    return result


# ---------------------------------------------------------------------------
# Manual answer key entry (no OCR)
# ---------------------------------------------------------------------------

class ManualAnswerKeyRequest(BaseModel):
    """JSON body: {answers: {"1": "A", "2": "B", ...}, weights: {"1": 2, "2": 1, ...}}"""
    answers: Dict[str, str]          # question_number (str) → letter
    weights: Dict[str, int] = {}     # question_number (str) → peso (optional)


@router.post(
    "/{exam_id}/answer-key/manual",
    status_code=status.HTTP_200_OK,
    summary="Set answer key manually (no OCR)",
)
async def set_answer_key_manual(
    exam_id: int,
    body: ManualAnswerKeyRequest,
    exam_repo: AsyncExamRepository = Depends(get_exam_repository),
    question_repo: AsyncQuestionRepository = Depends(get_question_repository),
):
    """
    Directly set correct answers for an exam without OCR.
    Accepts {answers: {"1": "A", "2": "B"}, weights: {"1": 2}}.
    Creates or updates Question records.
    """
    exam = await exam_repo.get_by_id(exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail=f"Exam {exam_id} not found")

    existing = await question_repo.get_by_exam_id(exam_id)
    existing_map = {q.numero: q for q in existing}

    to_create = []
    for q_str, answer in body.answers.items():
        try:
            q_num = int(q_str)
        except ValueError:
            continue
        answer = answer.strip().upper()
        if not answer:
            continue

        # Only apply a peso if the caller explicitly sent one for this question.
        # If no weight is provided, leave the existing peso untouched.
        explicit_peso = body.weights.get(q_str) or body.weights.get(str(q_num))

        if q_num in existing_map:
            q = existing_map[q_num]
            # Always update the answer
            await question_repo.update_answer_only(q.id, answer)
            # Only overwrite peso when the caller explicitly sent a weight
            if explicit_peso is not None:
                q.peso = int(explicit_peso)
                await question_repo.update(q)
        else:
            peso = int(explicit_peso) if explicit_peso is not None else 1
            to_create.append(Questao(
                exam_id=exam_id,
                numero=q_num,
                peso=peso,
                question_correct_answer=answer,
            ))

    if to_create:
        await question_repo.create_bulk(to_create)

    return {"saved": len(body.answers)}


# ---------------------------------------------------------------------------
# Manual answer sheet entry (no OCR)
# ---------------------------------------------------------------------------

class ManualAnswerSheetRequest(BaseModel):
    """JSON body: {answers: {"1": "A", "2": "B", ...}}"""
    answers: Dict[str, str]


@router.post(
    "/{exam_id}/participants/{participant_id}/manual-answers",
    status_code=status.HTTP_200_OK,
    summary="Submit participant answers manually (no OCR)",
)
async def submit_manual_answers(
    exam_id: int,
    participant_id: int,
    body: ManualAnswerSheetRequest,
    exam_repo: AsyncExamRepository = Depends(get_exam_repository),
    question_repo: AsyncQuestionRepository = Depends(get_question_repository),
    response_repo: AsyncResponseRepository = Depends(get_response_repository),
):
    """
    Directly record a participant's answers without OCR.
    Accepts {answers: {"1": "A", "2": "B"}}.
    Creates or updates Resposta records.
    """
    exam = await exam_repo.get_by_id(exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail=f"Exam {exam_id} not found")

    questions = await question_repo.get_by_exam_id(exam_id)
    question_map = {q.numero: q for q in questions}

    if not question_map:
        raise HTTPException(
            status_code=422,
            detail=f"No questions found for exam {exam_id}. Import the answer key first.",
        )

    saved = 0
    for q_str, answer in body.answers.items():
        try:
            q_num = int(q_str)
        except ValueError:
            continue
        answer = answer.strip().upper()
        if not answer or q_num not in question_map:
            continue
        q = question_map[q_num]
        resp = Resposta(
            user_id=participant_id,
            quest_id=q.id,
            exam_id=exam_id,
            marked_answer=answer,
            confidence_score=100.0,
            manually_reviewed=True,
        )
        await response_repo.create_or_update(resp)
        saved += 1

    return {"saved": saved}

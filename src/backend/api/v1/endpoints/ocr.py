from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from backend.api.dependencies import (
    get_exam_repository,
    get_question_repository,
    get_response_repository,
)
from backend.core.exceptions import NotFoundException, OCRProcessingException
from backend.repositories.implemations.async_exam_repo import AsyncExamRepository
from backend.repositories.implemations.async_question_repo import AsyncQuestionRepository
from backend.repositories.implemations.async_response_repo import AsyncResponseRepository
from backend.schemas.ocr import AnswerKeyResult, AnswerSheetResult
from backend.services.ocr.ocr_service import OCRService

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

    ocr_service = OCRService()
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

    ocr_service = OCRService()
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

    return result

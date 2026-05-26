import io
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_exam_history_service, get_score_calculator_service
from backend.core.exceptions import NotFoundException
from backend.schemas.scoring import ExamStatistics, ScoreBreakdown
from backend.services.exam_history_service import ExamHistoryService
from backend.services.score_calculator_service import ScoreCalculatorService

router = APIRouter(prefix="/exams", tags=["results"])


@router.get("/{exam_id}/results", response_model=List[ScoreBreakdown])
async def get_exam_results(
    exam_id: int,
    score_service: ScoreCalculatorService = Depends(get_score_calculator_service),
):
    """
    Get ranked participant list with scores for an exam.
    Requirements: 9.1, 9.2, 9.3
    """
    try:
        return await score_service.calculate_all_scores(exam_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.get("/{exam_id}/statistics", response_model=ExamStatistics)
async def get_exam_statistics(
    exam_id: int,
    score_service: ScoreCalculatorService = Depends(get_score_calculator_service),
):
    """
    Get aggregate statistics for an exam.
    Requirements: 9.4
    """
    try:
        return await score_service.calculate_exam_statistics(exam_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.get("/{exam_id}/export/excel")
async def export_exam_results_excel(
    exam_id: int,
    history_service: ExamHistoryService = Depends(get_exam_history_service),
):
    """
    Export exam results to Excel file.
    Requirements: 9.5
    """
    try:
        excel_bytes = await history_service.export_results_to_excel(exam_id)
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=exam_{exam_id}_results.xlsx"
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )

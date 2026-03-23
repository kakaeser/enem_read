from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.async_connection import AsyncDBConnectionHandler
from backend.repositories.implemations.async_exam_repo import AsyncExamRepository
from backend.repositories.implemations.async_participant_repo import AsyncParticipantRepository
from backend.repositories.implemations.async_question_repo import AsyncQuestionRepository
from backend.repositories.implemations.async_response_repo import AsyncResponseRepository
from backend.services.exam_history_service import ExamHistoryService
from backend.services.exam_manager_service import ExamManagerService
from backend.services.score_calculator_service import ScoreCalculatorService


async def get_db_session():
    """Yield an async database session."""
    async for session in AsyncDBConnectionHandler.get_session():
        yield session


def get_exam_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncExamRepository:
    return AsyncExamRepository(session)


def get_participant_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncParticipantRepository:
    return AsyncParticipantRepository(session)


def get_question_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncQuestionRepository:
    return AsyncQuestionRepository(session)


def get_response_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncResponseRepository:
    return AsyncResponseRepository(session)


def get_exam_manager_service(
    exam_repo: AsyncExamRepository = Depends(get_exam_repository),
    participant_repo: AsyncParticipantRepository = Depends(get_participant_repository),
) -> ExamManagerService:
    return ExamManagerService(exam_repo=exam_repo, participant_repo=participant_repo)


def get_score_calculator_service(
    exam_repo: AsyncExamRepository = Depends(get_exam_repository),
    participant_repo: AsyncParticipantRepository = Depends(get_participant_repository),
    question_repo: AsyncQuestionRepository = Depends(get_question_repository),
    response_repo: AsyncResponseRepository = Depends(get_response_repository),
) -> ScoreCalculatorService:
    return ScoreCalculatorService(
        exam_repo=exam_repo,
        participant_repo=participant_repo,
        question_repo=question_repo,
        response_repo=response_repo,
    )


def get_exam_history_service(
    exam_repo: AsyncExamRepository = Depends(get_exam_repository),
    participant_repo: AsyncParticipantRepository = Depends(get_participant_repository),
    question_repo: AsyncQuestionRepository = Depends(get_question_repository),
    response_repo: AsyncResponseRepository = Depends(get_response_repository),
    score_service: ScoreCalculatorService = Depends(get_score_calculator_service),
) -> ExamHistoryService:
    return ExamHistoryService(
        exam_repo=exam_repo,
        participant_repo=participant_repo,
        question_repo=question_repo,
        response_repo=response_repo,
        score_service=score_service,
    )

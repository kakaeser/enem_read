"""
Shared test fixtures using an in-memory SQLite database.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config.base import Base
# Import all entities so their tables are registered on Base.metadata
from backend.entities.exam import Exam
from backend.entities.participante import Participante
from backend.entities.questao import Questao
from backend.entities.resposta import Resposta

from backend.repositories.implemations.async_exam_repo import AsyncExamRepository
from backend.repositories.implemations.async_participant_repo import AsyncParticipantRepository
from backend.repositories.implemations.async_question_repo import AsyncQuestionRepository
from backend.repositories.implemations.async_response_repo import AsyncResponseRepository


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    """Create an in-memory async engine for tests."""
    eng = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Provide a transactional async session for each test."""
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with factory() as s:
        yield s


@pytest_asyncio.fixture
async def exam_repo(session):
    return AsyncExamRepository(session)


@pytest_asyncio.fixture
async def participant_repo(session):
    return AsyncParticipantRepository(session)


@pytest_asyncio.fixture
async def question_repo(session):
    return AsyncQuestionRepository(session)


@pytest_asyncio.fixture
async def response_repo(session):
    return AsyncResponseRepository(session)

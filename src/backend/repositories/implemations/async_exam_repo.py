from sqlalchemy import select, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from backend.entities.exam import Exam
from backend.repositories.interfaces.exam_interface import IExamRepository


class AsyncExamRepository(IExamRepository):
    """Async implementation of Exam repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, exam: Exam) -> Exam:
        """Create a new exam"""
        self.session.add(exam)
        await self.session.flush()
        await self.session.refresh(exam)
        return exam

    async def get_by_id(self, exam_id: int) -> Optional[Exam]:
        """Get exam by ID"""
        result = await self.session.execute(
            select(Exam).where(Exam.exam_id == exam_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Exam]:
        """Get all exams with pagination"""
        result = await self.session.execute(
            select(Exam)
            .order_by(Exam.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, exam: Exam) -> Exam:
        """Update an existing exam"""
        await self.session.merge(exam)
        await self.session.flush()
        await self.session.refresh(exam)
        return exam

    async def delete(self, exam_id: int) -> bool:
        """Delete an exam by ID.

        Uses ORM-style delete so SQLAlchemy's cascade='all, delete-orphan'
        fires and removes all related Questao, Participante, and Resposta rows.
        A bulk DELETE statement would bypass the ORM cascade entirely.
        """
        exam = await self.get_by_id(exam_id)
        if exam is None:
            return False
        await self.session.delete(exam)
        await self.session.flush()
        return True

    async def filter_by_status(self, status: str) -> List[Exam]:
        """Filter exams by status"""
        result = await self.session.execute(
            select(Exam)
            .where(Exam.status == status)
            .order_by(Exam.created_at.desc())
        )
        return list(result.scalars().all())

    async def search_by_name(self, name: str) -> List[Exam]:
        """Search exams by name (partial match)"""
        result = await self.session.execute(
            select(Exam)
            .where(Exam.exam_name.ilike(f"%{name}%"))
            .order_by(Exam.created_at.desc())
        )
        return list(result.scalars().all())

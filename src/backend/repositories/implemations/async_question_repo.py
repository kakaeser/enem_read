from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from backend.entities.questao import Questao
from backend.repositories.interfaces.question_interface import IQuestionRepository


class AsyncQuestionRepository(IQuestionRepository):
    """Async implementation of Question repository with bulk operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, question: Questao) -> Questao:
        """Create a single question"""
        self.session.add(question)
        await self.session.flush()
        await self.session.refresh(question)
        return question

    async def create_bulk(self, questions: List[Questao]) -> List[Questao]:
        """Create multiple questions in bulk"""
        self.session.add_all(questions)
        await self.session.flush()
        
        # Refresh all questions to get their IDs
        for question in questions:
            await self.session.refresh(question)
        
        return questions

    async def get_by_id(self, question_id: int) -> Optional[Questao]:
        """Get question by ID"""
        result = await self.session.execute(
            select(Questao).where(Questao.id == question_id)
        )
        return result.scalar_one_or_none()

    async def get_by_exam_id(self, exam_id: int) -> List[Questao]:
        """Get all questions for a specific exam"""
        result = await self.session.execute(
            select(Questao)
            .where(Questao.exam_id == exam_id)
            .order_by(Questao.numero)
        )
        return list(result.scalars().all())

    async def get_by_exam_and_number(self, exam_id: int, numero: int) -> Optional[Questao]:
        """Get question by exam ID and question number"""
        result = await self.session.execute(
            select(Questao)
            .where(Questao.exam_id == exam_id, Questao.numero == numero)
        )
        return result.scalar_one_or_none()

    async def update(self, question: Questao) -> Questao:
        """Update an existing question (full object merge)."""
        await self.session.merge(question)
        await self.session.flush()
        await self.session.refresh(question)
        return question

    async def update_answer_only(self, question_id: int, correct_answer: str) -> None:
        """
        Update ONLY the question_correct_answer column.

        Uses a targeted SQL UPDATE so that peso and all other fields are
        guaranteed to remain untouched, regardless of what the in-memory
        object contains.
        """
        await self.session.execute(
            update(Questao)
            .where(Questao.id == question_id)
            .values(question_correct_answer=correct_answer)
        )
        await self.session.flush()

    async def delete(self, question_id: int) -> bool:
        """Delete a question by ID"""
        result = await self.session.execute(
            delete(Questao).where(Questao.id == question_id)
        )
        return result.rowcount > 0

    async def delete_by_exam_id(self, exam_id: int) -> bool:
        """Delete all questions for a specific exam"""
        result = await self.session.execute(
            delete(Questao).where(Questao.exam_id == exam_id)
        )
        return result.rowcount > 0

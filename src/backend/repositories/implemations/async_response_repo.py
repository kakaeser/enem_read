from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from backend.entities.resposta import Resposta
from backend.repositories.interfaces.response_interface import IResponseRepository


class AsyncResponseRepository(IResponseRepository):
    """Async implementation of Response repository with upsert support"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, response: Resposta) -> Resposta:
        """Create a new response"""
        self.session.add(response)
        await self.session.flush()
        await self.session.refresh(response)
        return response

    async def create_or_update(self, response: Resposta) -> Resposta:
        """
        Create a new response or update if exists (upsert).
        Checks for existing response by user_id and quest_id.
        """
        # Check if response already exists
        existing = await self.get_by_participant_and_question(
            response.user_id, response.quest_id
        )
        
        if existing:
            # Update existing response
            existing.marked_answer = response.marked_answer
            existing.confidence_score = response.confidence_score
            existing.manually_reviewed = response.manually_reviewed
            existing.exam_id = response.exam_id
            
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            # Create new response
            return await self.create(response)

    async def get_by_id(self, response_id: int) -> Optional[Resposta]:
        """Get response by ID"""
        result = await self.session.execute(
            select(Resposta).where(Resposta.id == response_id)
        )
        return result.scalar_one_or_none()

    async def get_by_participant_and_question(
        self, user_id: int, quest_id: int
    ) -> Optional[Resposta]:
        """Get response by participant and question"""
        result = await self.session.execute(
            select(Resposta)
            .where(Resposta.user_id == user_id, Resposta.quest_id == quest_id)
        )
        return result.scalar_one_or_none()

    async def get_by_participant_and_exam(
        self, user_id: int, exam_id: int
    ) -> List[Resposta]:
        """Get all responses for a participant in a specific exam"""
        result = await self.session.execute(
            select(Resposta)
            .where(Resposta.user_id == user_id, Resposta.exam_id == exam_id)
            .order_by(Resposta.quest_id)
        )
        return list(result.scalars().all())

    async def get_by_exam_id(self, exam_id: int) -> List[Resposta]:
        """Get all responses for a specific exam"""
        result = await self.session.execute(
            select(Resposta)
            .where(Resposta.exam_id == exam_id)
            .order_by(Resposta.user_id, Resposta.quest_id)
        )
        return list(result.scalars().all())

    async def update(self, response: Resposta) -> Resposta:
        """Update an existing response"""
        await self.session.merge(response)
        await self.session.flush()
        await self.session.refresh(response)
        return response

    async def delete(self, response_id: int) -> bool:
        """Delete a response by ID"""
        result = await self.session.execute(
            delete(Resposta).where(Resposta.id == response_id)
        )
        return result.rowcount > 0

    async def delete_by_exam_id(self, exam_id: int) -> bool:
        """Delete all responses for a specific exam"""
        result = await self.session.execute(
            delete(Resposta).where(Resposta.exam_id == exam_id)
        )
        return result.rowcount > 0

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from backend.entities.participante import Participante
from backend.repositories.interfaces.participant_interface import IParticipantRepository


class AsyncParticipantRepository(IParticipantRepository):
    """Async implementation of Participant repository with exam filtering"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, participant: Participante) -> Participante:
        """Create a new participant"""
        self.session.add(participant)
        await self.session.flush()
        await self.session.refresh(participant)
        return participant

    async def create_bulk(self, participants: List[Participante]) -> List[Participante]:
        """Create multiple participants in bulk"""
        self.session.add_all(participants)
        await self.session.flush()
        
        # Refresh all participants to get their IDs
        for participant in participants:
            await self.session.refresh(participant)
        
        return participants

    async def get_by_id(self, participant_id: int) -> Optional[Participante]:
        """Get participant by ID"""
        result = await self.session.execute(
            select(Participante).where(Participante.id == participant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_exam_id(self, exam_id: int) -> List[Participante]:
        """Get all participants for a specific exam"""
        result = await self.session.execute(
            select(Participante)
            .where(Participante.exam_id == exam_id)
            .order_by(Participante.nome)
        )
        return list(result.scalars().all())

    async def get_by_exam_and_name(self, exam_id: int, nome: str) -> Optional[Participante]:
        """Get participant by exam ID and name"""
        result = await self.session.execute(
            select(Participante)
            .where(Participante.exam_id == exam_id, Participante.nome == nome)
        )
        return result.scalar_one_or_none()

    async def get_present_by_exam_id(self, exam_id: int) -> List[Participante]:
        """Get all present participants for a specific exam"""
        result = await self.session.execute(
            select(Participante)
            .where(Participante.exam_id == exam_id, Participante.presente == True)
            .order_by(Participante.nome)
        )
        return list(result.scalars().all())

    async def get_absent_by_exam_id(self, exam_id: int) -> List[Participante]:
        """Get all absent participants for a specific exam"""
        result = await self.session.execute(
            select(Participante)
            .where(Participante.exam_id == exam_id, Participante.presente == False)
            .order_by(Participante.nome)
        )
        return list(result.scalars().all())

    async def update(self, participant: Participante) -> Participante:
        """Update an existing participant"""
        await self.session.merge(participant)
        await self.session.flush()
        await self.session.refresh(participant)
        return participant

    async def delete(self, participant_id: int) -> bool:
        """Delete a participant by ID"""
        result = await self.session.execute(
            delete(Participante).where(Participante.id == participant_id)
        )
        return result.rowcount > 0

    async def delete_by_exam_id(self, exam_id: int) -> bool:
        """Delete all participants for a specific exam"""
        result = await self.session.execute(
            delete(Participante).where(Participante.exam_id == exam_id)
        )
        return result.rowcount > 0

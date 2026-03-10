from abc import ABC, abstractmethod
from typing import List, Optional
from backend.entities.participante import Participante


class IParticipantRepository(ABC):
    """Interface for Participant repository with async operations and exam filtering"""

    @abstractmethod
    async def create(self, participant: Participante) -> Participante:
        """Create a new participant"""
        pass

    @abstractmethod
    async def create_bulk(self, participants: List[Participante]) -> List[Participante]:
        """Create multiple participants in bulk"""
        pass

    @abstractmethod
    async def get_by_id(self, participant_id: int) -> Optional[Participante]:
        """Get participant by ID"""
        pass

    @abstractmethod
    async def get_by_exam_id(self, exam_id: int) -> List[Participante]:
        """Get all participants for a specific exam"""
        pass

    @abstractmethod
    async def get_by_exam_and_name(self, exam_id: int, nome: str) -> Optional[Participante]:
        """Get participant by exam ID and name"""
        pass

    @abstractmethod
    async def get_present_by_exam_id(self, exam_id: int) -> List[Participante]:
        """Get all present participants for a specific exam"""
        pass

    @abstractmethod
    async def update(self, participant: Participante) -> Participante:
        """Update an existing participant"""
        pass

    @abstractmethod
    async def delete(self, participant_id: int) -> bool:
        """Delete a participant by ID"""
        pass

    @abstractmethod
    async def delete_by_exam_id(self, exam_id: int) -> bool:
        """Delete all participants for a specific exam"""
        pass

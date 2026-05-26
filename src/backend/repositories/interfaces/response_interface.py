from abc import ABC, abstractmethod
from typing import List, Optional
from backend.entities.resposta import Resposta


class IResponseRepository(ABC):
    """Interface for Response repository with async operations and upsert support"""

    @abstractmethod
    async def create(self, response: Resposta) -> Resposta:
        """Create a new response"""
        pass

    @abstractmethod
    async def create_or_update(self, response: Resposta) -> Resposta:
        """Create a new response or update if exists (upsert)"""
        pass

    @abstractmethod
    async def get_by_id(self, response_id: int) -> Optional[Resposta]:
        """Get response by ID"""
        pass

    @abstractmethod
    async def get_by_participant_and_question(
        self, user_id: int, quest_id: int
    ) -> Optional[Resposta]:
        """Get response by participant and question"""
        pass

    @abstractmethod
    async def get_by_participant_and_exam(
        self, user_id: int, exam_id: int
    ) -> List[Resposta]:
        """Get all responses for a participant in a specific exam"""
        pass

    @abstractmethod
    async def get_by_exam_id(self, exam_id: int) -> List[Resposta]:
        """Get all responses for a specific exam"""
        pass

    @abstractmethod
    async def update(self, response: Resposta) -> Resposta:
        """Update an existing response"""
        pass

    @abstractmethod
    async def delete(self, response_id: int) -> bool:
        """Delete a response by ID"""
        pass

    @abstractmethod
    async def delete_by_exam_id(self, exam_id: int) -> bool:
        """Delete all responses for a specific exam"""
        pass

from abc import ABC, abstractmethod
from typing import List, Optional
from backend.entities.exam import Exam


class IExamRepository(ABC):
    """Interface for Exam repository with async CRUD operations"""

    @abstractmethod
    async def create(self, exam: Exam) -> Exam:
        """Create a new exam"""
        pass

    @abstractmethod
    async def get_by_id(self, exam_id: int) -> Optional[Exam]:
        """Get exam by ID"""
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Exam]:
        """Get all exams with pagination"""
        pass

    @abstractmethod
    async def update(self, exam: Exam) -> Exam:
        """Update an existing exam"""
        pass

    @abstractmethod
    async def delete(self, exam_id: int) -> bool:
        """Delete an exam by ID (cascade deletes related entities)"""
        pass

    @abstractmethod
    async def filter_by_status(self, status: str) -> List[Exam]:
        """Filter exams by status"""
        pass

    @abstractmethod
    async def search_by_name(self, name: str) -> List[Exam]:
        """Search exams by name (partial match)"""
        pass

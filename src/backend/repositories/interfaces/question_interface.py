from abc import ABC, abstractmethod
from typing import List, Optional
from backend.entities.questao import Questao


class IQuestionRepository(ABC):
    """Interface for Question repository with async operations and bulk support"""

    @abstractmethod
    async def create(self, question: Questao) -> Questao:
        """Create a single question"""
        pass

    @abstractmethod
    async def create_bulk(self, questions: List[Questao]) -> List[Questao]:
        """Create multiple questions in bulk"""
        pass

    @abstractmethod
    async def get_by_id(self, question_id: int) -> Optional[Questao]:
        """Get question by ID"""
        pass

    @abstractmethod
    async def get_by_exam_id(self, exam_id: int) -> List[Questao]:
        """Get all questions for a specific exam"""
        pass

    @abstractmethod
    async def get_by_exam_and_number(self, exam_id: int, numero: int) -> Optional[Questao]:
        """Get question by exam ID and question number"""
        pass

    @abstractmethod
    async def update(self, question: Questao) -> Questao:
        """Update an existing question"""
        pass

    @abstractmethod
    async def update_answer_only(self, question_id: int, correct_answer: str) -> None:
        """Update ONLY the question_correct_answer column, leaving peso untouched."""
        pass

    @abstractmethod
    async def delete(self, question_id: int) -> bool:
        """Delete a question by ID"""
        pass

    @abstractmethod
    async def delete_by_exam_id(self, exam_id: int) -> bool:
        """Delete all questions for a specific exam"""
        pass

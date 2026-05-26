from typing import List, Optional
from datetime import datetime

from backend.entities.exam import Exam
from backend.entities.participante import Participante
from backend.entities.questao import Questao
from backend.repositories.interfaces.exam_interface import IExamRepository
from backend.repositories.interfaces.participant_interface import IParticipantRepository
from backend.repositories.interfaces.question_interface import IQuestionRepository
from backend.schemas.exam import ExamCreate, ExamUpdate, ExamResponse
from backend.schemas.participante import ParticipantCreate, ParticipantResponse


class ExamManagerService:
    """Service for creating and managing exam sessions with dependency-injected repositories."""

    def __init__(
        self,
        exam_repo: IExamRepository,
        participant_repo: IParticipantRepository,
        question_repo: Optional[IQuestionRepository] = None,
    ):
        self.exam_repo = exam_repo
        self.participant_repo = participant_repo
        self.question_repo = question_repo

    async def create_exam(self, exam_data: ExamCreate) -> ExamResponse:
        """Create a new exam session and pre-create Question rows with weights."""
        exam = Exam(
            exam_name=exam_data.exam_name,
            questions_numbers=exam_data.questions_numbers,
            symbolic_note=exam_data.symbolic_note,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status="draft",
        )
        created = await self.exam_repo.create(exam)

        # Pre-create question rows with weights so the answer key can be set later
        if self.question_repo is not None:
            n = exam_data.questions_numbers
            weights = _compute_weights(n, exam_data.weight_mode, exam_data.heavy_questions)

            questions = [
                Questao(
                    exam_id=created.exam_id,
                    numero=i + 1,
                    peso=weights[i],
                    question_correct_answer=None,
                )
                for i in range(n)
            ]
            await self.question_repo.create_bulk(questions)

        return ExamResponse.model_validate(created)

    async def get_exam(self, exam_id: int) -> ExamResponse:
        """Get exam by ID. Requirements: 1.1"""
        exam = await self.exam_repo.get_by_id(exam_id)
        if exam is None:
            raise ValueError(f"Exam with id {exam_id} not found")
        return ExamResponse.model_validate(exam)

    async def update_exam(self, exam_id: int, exam_data: ExamUpdate) -> ExamResponse:
        """Update exam configuration fields. Requirements: 1.6"""
        exam = await self.exam_repo.get_by_id(exam_id)
        if exam is None:
            raise ValueError(f"Exam with id {exam_id} not found")

        update_fields = exam_data.model_dump(exclude_none=True)
        for field, value in update_fields.items():
            setattr(exam, field, value)
        exam.updated_at = datetime.utcnow()

        updated = await self.exam_repo.update(exam)
        return ExamResponse.model_validate(updated)

    async def delete_exam(self, exam_id: int) -> bool:
        """Delete exam and cascade-delete all associated data. Requirements: 1.7"""
        exam = await self.exam_repo.get_by_id(exam_id)
        if exam is None:
            raise ValueError(f"Exam with id {exam_id} not found")
        return await self.exam_repo.delete(exam_id)

    async def list_exams(
        self,
        status: Optional[str] = None,
        name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ExamResponse]:
        """List exams with optional filtering by status or name. Requirements: 1.1"""
        if status:
            exams = await self.exam_repo.filter_by_status(status)
        elif name:
            exams = await self.exam_repo.search_by_name(name)
        else:
            exams = await self.exam_repo.get_all(skip=skip, limit=limit)
        return [ExamResponse.model_validate(e) for e in exams]

    async def add_participant_to_exam(
        self, exam_id: int, participant_data: ParticipantCreate
    ) -> ParticipantResponse:
        """
        Manually add a participant to an exam.
        Warns (but allows) duplicate names within the same exam.
        Requirements: 17.1, 17.2, 17.3, 17.4
        """
        exam = await self.exam_repo.get_by_id(exam_id)
        if exam is None:
            raise ValueError(f"Exam with id {exam_id} not found")

        # Validate name length (Req 17.3)
        nome = participant_data.nome.strip()
        if not nome:
            raise ValueError("Participant name must not be empty")

        participant = Participante(
            exam_id=exam_id,
            nome=nome,
            presente=False,  # default per Req 17.5
            essay_points=0.0,
        )
        created = await self.participant_repo.create(participant)
        return ParticipantResponse.model_validate(created)


# ---------------------------------------------------------------------------
# Weight computation helper
# ---------------------------------------------------------------------------

def _compute_weights(
    n: int,
    weight_mode: str,
    heavy_questions: list[int] | None,
) -> list[int]:
    """
    Return a list of `n` peso values (1 or 2) based on weight_mode.

    Modes:
      "default"        — all 1
      "even_questions" — even-numbered questions (2,4,6…) get 2, others 1
      "odd_questions"  — odd-numbered questions (1,3,5…) get 2, others 1
      "custom"         — questions in heavy_questions get 2, others 1
    """
    if weight_mode == "even_questions":
        return [2 if (i + 1) % 2 == 0 else 1 for i in range(n)]
    if weight_mode == "odd_questions":
        return [2 if (i + 1) % 2 != 0 else 1 for i in range(n)]
    if weight_mode == "custom" and heavy_questions:
        heavy_set = set(heavy_questions)
        return [2 if (i + 1) in heavy_set else 1 for i in range(n)]
    # default
    return [1] * n

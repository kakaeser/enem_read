from typing import List, Optional
from io import BytesIO
import statistics

import pandas as pd

from backend.repositories.interfaces.exam_interface import IExamRepository
from backend.repositories.interfaces.participant_interface import IParticipantRepository
from backend.repositories.interfaces.question_interface import IQuestionRepository
from backend.repositories.interfaces.response_interface import IResponseRepository
from backend.schemas.exam import ExamResponse
from backend.schemas.participante import ParticipantResponse
from backend.schemas.questao import QuestionResponse
from backend.schemas.scoring import ScoreBreakdown, ExamStatistics
from backend.services.score_calculator_service import ScoreCalculatorService


class ExamHistoryService:
    """
    Retrieves historical exam data, generates result reports, and exports to Excel.
    Requirements: 8.1–8.5, 9.1–9.7
    """

    def __init__(
        self,
        exam_repo: IExamRepository,
        participant_repo: IParticipantRepository,
        question_repo: IQuestionRepository,
        response_repo: IResponseRepository,
        score_service: ScoreCalculatorService,
    ):
        self.exam_repo = exam_repo
        self.participant_repo = participant_repo
        self.question_repo = question_repo
        self.response_repo = response_repo
        self.score_service = score_service

    # ------------------------------------------------------------------ #
    # Exam listing / details  (Req 8.1–8.5)
    # ------------------------------------------------------------------ #

    async def list_exams(
        self,
        name_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        """
        List all exams ordered by creation date descending.
        Supports partial name search and status filtering. Req 8.1, 8.6, 8.7
        """
        if name_filter:
            exams = await self.exam_repo.search_by_name(name_filter)
        elif status_filter:
            exams = await self.exam_repo.filter_by_status(status_filter)
        else:
            exams = await self.exam_repo.get_all(skip=skip, limit=limit)

        result = []
        for exam in exams:
            participants = await self.participant_repo.get_by_exam_id(exam.exam_id)
            questions = await self.question_repo.get_by_exam_id(exam.exam_id)
            result.append({
                "exam_id": exam.exam_id,
                "exam_name": exam.exam_name,
                "status": exam.status,
                "created_at": exam.created_at,
                "updated_at": exam.updated_at,
                "total_participants": len(participants),
                "total_questions": len(questions),
            })
        return result

    async def get_exam_details(self, exam_id: int) -> dict:
        """
        Full exam details including participants and questions. Req 8.3, 8.4, 8.5
        """
        exam = await self.exam_repo.get_by_id(exam_id)
        if exam is None:
            raise ValueError(f"Exam {exam_id} not found")

        participants = await self.participant_repo.get_by_exam_id(exam_id)
        questions = await self.question_repo.get_by_exam_id(exam_id)

        return {
            "exam": ExamResponse.model_validate(exam),
            "participants": [ParticipantResponse.model_validate(p) for p in participants],
            "questions": [QuestionResponse.model_validate(q) for q in questions],
        }

    # ------------------------------------------------------------------ #
    # Results & ranking  (Req 9.1–9.4)
    # ------------------------------------------------------------------ #

    async def get_exam_results(self, exam_id: int) -> List[ScoreBreakdown]:
        """
        Ranked participant list with raw, normalized, and final scores.
        Req 9.1, 9.2, 9.3
        """
        exam = await self.exam_repo.get_by_id(exam_id)
        if exam is None:
            raise ValueError(f"Exam {exam_id} not found")
        return await self.score_service.calculate_all_scores(exam_id)

    async def get_question_statistics(self, exam_id: int) -> List[dict]:
        """
        Per-question correct-answer rate and difficulty analysis. Req 9.6, 9.7
        """
        questions = await self.question_repo.get_by_exam_id(exam_id)
        responses = await self.response_repo.get_by_exam_id(exam_id)
        participants = await self.participant_repo.get_by_exam_id(exam_id)
        total_participants = len(participants)

        stats = []
        for q in questions:
            if not q.question_correct_answer:
                continue
            q_responses = [r for r in responses if r.quest_id == q.id]
            correct = sum(
                1 for r in q_responses
                if r.marked_answer
                and r.marked_answer.strip().upper() == q.question_correct_answer.strip().upper()
            )
            rate = (correct / total_participants * 100) if total_participants > 0 else 0.0
            stats.append({
                "question_id": q.id,
                "numero": q.numero,
                "peso": q.peso,
                "correct_answer": q.question_correct_answer,
                "correct_count": correct,
                "total_responses": len(q_responses),
                "correct_rate_percentage": round(rate, 2),
            })

        # Sort by correct_rate ascending so hardest questions appear first (Req 9.7)
        stats.sort(key=lambda x: x["correct_rate_percentage"])
        return stats

    # ------------------------------------------------------------------ #
    # Aggregate statistics  (Req 9.4)
    # ------------------------------------------------------------------ #

    async def get_aggregate_statistics(self, exam_id: int) -> ExamStatistics:
        """Average, median, highest, lowest scores for an exam."""
        return await self.score_service.calculate_exam_statistics(exam_id)

    # ------------------------------------------------------------------ #
    # Excel export  (Req 9.5, 18.12)
    # ------------------------------------------------------------------ #

    async def export_results_to_excel(self, exam_id: int) -> bytes:
        """
        Export exam results to Excel with participant names, scores, and
        per-question answer breakdown. Req 9.5, 18.12
        """
        exam = await self.exam_repo.get_by_id(exam_id)
        if exam is None:
            raise ValueError(f"Exam {exam_id} not found")

        scores = await self.score_service.calculate_all_scores(exam_id)
        questions = await self.question_repo.get_by_exam_id(exam_id)
        responses = await self.response_repo.get_by_exam_id(exam_id)

        # Build response lookup: (user_id, quest_id) -> marked_answer
        resp_map = {(r.user_id, r.quest_id): r.marked_answer for r in responses}

        rows = []
        for rank, score in enumerate(scores, start=1):
            row: dict = {
                "Rank": rank,
                "Nome": score.participant_name,
                "Nota Bruta": round(score.raw_score, 2),
                "Nota Normalizada": round(score.normalized_score, 2),
                "Pontos Redação": round(score.essay_points, 2),
                "Nota Final": round(score.final_score, 2),
                "Acertos": score.correct_count,
                "Total Questões": score.total_questions,
                "Aproveitamento (%)": round(score.accuracy_percentage, 2),
            }
            # Per-question columns
            for q in questions:
                col = f"Q{q.numero}"
                row[col] = resp_map.get((score.participant_id, q.id), "")
            rows.append(row)

        df = pd.DataFrame(rows)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Resultados")

            # Second sheet: question statistics
            q_stats = await self.get_question_statistics(exam_id)
            if q_stats:
                df_stats = pd.DataFrame(q_stats)
                df_stats.to_excel(writer, index=False, sheet_name="Estatísticas Questões")

        return output.getvalue()

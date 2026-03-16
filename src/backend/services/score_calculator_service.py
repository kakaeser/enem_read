from typing import List
import statistics

from backend.repositories.interfaces.exam_interface import IExamRepository
from backend.repositories.interfaces.participant_interface import IParticipantRepository
from backend.repositories.interfaces.question_interface import IQuestionRepository
from backend.repositories.interfaces.response_interface import IResponseRepository
from backend.schemas.scoring import ScoreBreakdown, ExamStatistics


class ScoreCalculatorService:
    """
    Calculates participant scores by comparing marked answers with correct answers.
    Requirements: 7.1–7.7, 18.7, 18.8, 9.4
    """

    def __init__(
        self,
        exam_repo: IExamRepository,
        participant_repo: IParticipantRepository,
        question_repo: IQuestionRepository,
        response_repo: IResponseRepository,
    ):
        self.exam_repo = exam_repo
        self.participant_repo = participant_repo
        self.question_repo = question_repo
        self.response_repo = response_repo

    async def calculate_participant_score(
        self, participant_id: int, exam_id: int
    ) -> ScoreBreakdown:
        """
        Calculate score for a single participant.
        - Compares marked_answer vs question_correct_answer (case-insensitive, Req 7.2)
        - Null/empty marked_answer counts as incorrect (Req 7.6)
        - Questions with null correct_answer are excluded (Req 7.7)
        - final_score = normalized_score + essay_points (Req 18.8)
        """
        participant = await self.participant_repo.get_by_id(participant_id)
        if participant is None:
            raise ValueError(f"Participant {participant_id} not found")

        questions = await self.question_repo.get_by_exam_id(exam_id)
        responses = await self.response_repo.get_by_participant_and_exam(
            participant_id, exam_id
        )

        # Build lookup: question_id -> response
        response_map = {r.quest_id: r for r in responses}

        raw_score = 0.0
        total_possible_score = 0.0
        correct_count = 0
        gradable_questions = 0

        for q in questions:
            # Skip questions without a correct answer (Req 7.7)
            if not q.question_correct_answer:
                continue

            gradable_questions += 1
            total_possible_score += q.peso

            resp = response_map.get(q.id)
            marked = resp.marked_answer if resp else None

            # Case-insensitive comparison; null/empty = incorrect (Req 7.1, 7.2, 7.6)
            if marked and marked.strip().upper() == q.question_correct_answer.strip().upper():
                raw_score += q.peso
                correct_count += 1

        # Normalized score formula: (raw / total_possible) * symbolic_note (Req 7.5)
        exam_symbolic_note = await self._get_symbolic_note(exam_id)
        if total_possible_score > 0:
            normalized_score = (raw_score / total_possible_score) * exam_symbolic_note
        else:
            normalized_score = 0.0

        essay_points = participant.essay_points or 0.0
        final_score = normalized_score + essay_points  # Req 18.8

        accuracy = (correct_count / gradable_questions * 100) if gradable_questions > 0 else 0.0

        return ScoreBreakdown(
            participant_id=participant_id,
            participant_name=participant.nome,
            raw_score=raw_score,
            total_possible_score=total_possible_score,
            normalized_score=normalized_score,
            essay_points=essay_points,
            final_score=final_score,
            correct_count=correct_count,
            total_questions=gradable_questions,
            accuracy_percentage=accuracy,
        )

    async def calculate_all_scores(self, exam_id: int) -> List[ScoreBreakdown]:
        """Batch score calculation for all participants in an exam. Req 7.8"""
        participants = await self.participant_repo.get_by_exam_id(exam_id)
        results = []
        for p in participants:
            breakdown = await self.calculate_participant_score(p.id, exam_id)
            results.append(breakdown)
        # Sort by final_score descending
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results

    async def get_score_breakdown(
        self, participant_id: int, exam_id: int
    ) -> ScoreBreakdown:
        """Detailed score breakdown for a single participant. Req 9.4"""
        return await self.calculate_participant_score(participant_id, exam_id)

    async def calculate_exam_statistics(self, exam_id: int) -> ExamStatistics:
        """Aggregate statistics for an exam. Req 9.4"""
        participants = await self.participant_repo.get_by_exam_id(exam_id)
        total_participants = len(participants)

        all_scores = await self.calculate_all_scores(exam_id)

        # Participants with at least one response
        responses_all = await self.response_repo.get_by_exam_id(exam_id)
        participants_with_responses = len({r.user_id for r in responses_all})

        final_scores = [s.final_score for s in all_scores]

        if final_scores:
            avg = sum(final_scores) / len(final_scores)
            med = statistics.median(final_scores)
            highest = max(final_scores)
            lowest = min(final_scores)
            std = statistics.stdev(final_scores) if len(final_scores) > 1 else 0.0
        else:
            avg = med = highest = lowest = std = 0.0

        return ExamStatistics(
            exam_id=exam_id,
            total_participants=total_participants,
            participants_with_submissions=participants_with_responses,
            average_score=avg,
            median_score=med,
            highest_score=highest,
            lowest_score=lowest,
            std_deviation=std,
        )

    async def _get_symbolic_note(self, exam_id: int) -> float:
        """Retrieve symbolic_note for the exam to use in normalization."""
        exam = await self.exam_repo.get_by_id(exam_id)
        return float(exam.symbolic_note) if exam else 1000.0

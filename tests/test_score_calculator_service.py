"""
Unit tests for ScoreCalculatorService.
Requirements: 7.1-7.7, 18.7, 18.8, 9.4
"""
import pytest

from backend.entities.exam import Exam
from backend.entities.participante import Participante
from backend.entities.questao import Questao
from backend.entities.resposta import Resposta
from backend.schemas.exam import ExamCreate
from backend.services.score_calculator_service import ScoreCalculatorService


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def make_service(exam_repo, participant_repo, question_repo, response_repo):
    return ScoreCalculatorService(
        exam_repo=exam_repo,
        participant_repo=participant_repo,
        question_repo=question_repo,
        response_repo=response_repo,
    )


async def _seed_exam(session, exam_repo, symbolic_note=100):
    """Create a minimal exam and return it."""
    exam = Exam(exam_name="Test Exam", questions_numbers=3, symbolic_note=symbolic_note, status="draft")
    session.add(exam)
    await session.flush()
    await session.refresh(exam)
    return exam


async def _seed_participant(session, exam_id, nome="Alice", essay_points=0.0):
    p = Participante(exam_id=exam_id, nome=nome, presente=True, essay_points=essay_points)
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p


async def _seed_question(session, exam_id, numero, correct_answer, peso=1):
    q = Questao(exam_id=exam_id, numero=numero, peso=peso, question_correct_answer=correct_answer)
    session.add(q)
    await session.flush()
    await session.refresh(q)
    return q


async def _seed_response(session, user_id, quest_id, exam_id, marked_answer):
    r = Resposta(user_id=user_id, quest_id=quest_id, exam_id=exam_id, marked_answer=marked_answer)
    session.add(r)
    await session.flush()
    await session.refresh(r)
    return r


# ------------------------------------------------------------------ #
# calculate_participant_score - basic correctness
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_all_correct_answers(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 7.1, 7.2 - correct answers are counted."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=100)
    p = await _seed_participant(session, exam.exam_id)
    q1 = await _seed_question(session, exam.exam_id, 1, "A", peso=1)
    q2 = await _seed_question(session, exam.exam_id, 2, "B", peso=1)
    q3 = await _seed_question(session, exam.exam_id, 3, "C", peso=1)
    await _seed_response(session, p.id, q1.id, exam.exam_id, "A")
    await _seed_response(session, p.id, q2.id, exam.exam_id, "B")
    await _seed_response(session, p.id, q3.id, exam.exam_id, "C")

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    result = await svc.calculate_participant_score(p.id, exam.exam_id)

    assert result.correct_count == 3
    assert result.raw_score == 3.0
    assert result.total_possible_score == 3.0
    assert result.normalized_score == pytest.approx(100.0)
    assert result.final_score == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_no_correct_answers(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 7.1 - wrong answers score zero."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=100)
    p = await _seed_participant(session, exam.exam_id)
    q1 = await _seed_question(session, exam.exam_id, 1, "A")
    await _seed_response(session, p.id, q1.id, exam.exam_id, "B")

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    result = await svc.calculate_participant_score(p.id, exam.exam_id)

    assert result.correct_count == 0
    assert result.raw_score == 0.0
    assert result.normalized_score == 0.0


@pytest.mark.asyncio
async def test_case_insensitive_comparison(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 7.2 - comparison is case-insensitive."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=100)
    p = await _seed_participant(session, exam.exam_id)
    q = await _seed_question(session, exam.exam_id, 1, "A")
    await _seed_response(session, p.id, q.id, exam.exam_id, "a")  # lowercase

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    result = await svc.calculate_participant_score(p.id, exam.exam_id)

    assert result.correct_count == 1


@pytest.mark.asyncio
async def test_null_marked_answer_is_incorrect(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 7.6 - null/empty marked_answer counts as incorrect."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=100)
    p = await _seed_participant(session, exam.exam_id)
    q = await _seed_question(session, exam.exam_id, 1, "A")
    await _seed_response(session, p.id, q.id, exam.exam_id, None)

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    result = await svc.calculate_participant_score(p.id, exam.exam_id)

    assert result.correct_count == 0


@pytest.mark.asyncio
async def test_missing_response_is_incorrect(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 7.6 - no response for a question counts as incorrect."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=100)
    p = await _seed_participant(session, exam.exam_id)
    await _seed_question(session, exam.exam_id, 1, "A")  # no response created

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    result = await svc.calculate_participant_score(p.id, exam.exam_id)

    assert result.correct_count == 0
    assert result.raw_score == 0.0


@pytest.mark.asyncio
async def test_question_without_correct_answer_excluded(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 7.7 - questions with null correct_answer are excluded from scoring."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=100)
    p = await _seed_participant(session, exam.exam_id)
    q_graded = await _seed_question(session, exam.exam_id, 1, "A", peso=1)
    q_ungraded = await _seed_question(session, exam.exam_id, 2, None, peso=1)  # no correct answer
    await _seed_response(session, p.id, q_graded.id, exam.exam_id, "A")
    await _seed_response(session, p.id, q_ungraded.id, exam.exam_id, "B")

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    result = await svc.calculate_participant_score(p.id, exam.exam_id)

    assert result.total_questions == 1  # only graded question counted
    assert result.total_possible_score == 1.0


# ------------------------------------------------------------------ #
# Normalized score formula (Req 7.5)
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_normalized_score_formula(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 7.5 - normalized = (raw / total_possible) * symbolic_note."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=1000)
    p = await _seed_participant(session, exam.exam_id)
    q1 = await _seed_question(session, exam.exam_id, 1, "A", peso=2)
    q2 = await _seed_question(session, exam.exam_id, 2, "B", peso=3)
    await _seed_response(session, p.id, q1.id, exam.exam_id, "A")  # correct, peso=2
    await _seed_response(session, p.id, q2.id, exam.exam_id, "C")  # wrong

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    result = await svc.calculate_participant_score(p.id, exam.exam_id)

    # raw=2, total_possible=5, symbolic=1000 → normalized = 2/5 * 1000 = 400
    assert result.raw_score == pytest.approx(2.0)
    assert result.total_possible_score == pytest.approx(5.0)
    assert result.normalized_score == pytest.approx(400.0)


# ------------------------------------------------------------------ #
# Essay points (Req 18.7, 18.8)
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_essay_points_added_to_final_score(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 18.8 - final_score = normalized_score + essay_points."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=100)
    p = await _seed_participant(session, exam.exam_id, essay_points=50.0)
    q = await _seed_question(session, exam.exam_id, 1, "A", peso=1)
    await _seed_response(session, p.id, q.id, exam.exam_id, "A")

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    result = await svc.calculate_participant_score(p.id, exam.exam_id)

    assert result.essay_points == pytest.approx(50.0)
    assert result.final_score == pytest.approx(result.normalized_score + 50.0)


@pytest.mark.asyncio
async def test_zero_essay_points_no_effect(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 18.7 - zero essay_points doesn't change score."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=100)
    p = await _seed_participant(session, exam.exam_id, essay_points=0.0)
    q = await _seed_question(session, exam.exam_id, 1, "A")
    await _seed_response(session, p.id, q.id, exam.exam_id, "A")

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    result = await svc.calculate_participant_score(p.id, exam.exam_id)

    assert result.final_score == pytest.approx(result.normalized_score)


# ------------------------------------------------------------------ #
# calculate_all_scores
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_calculate_all_scores_sorted_descending(session, exam_repo, participant_repo, question_repo, response_repo):
    """Results are sorted by final_score descending."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=100)
    p1 = await _seed_participant(session, exam.exam_id, nome="Alice")
    p2 = await _seed_participant(session, exam.exam_id, nome="Bob")
    q = await _seed_question(session, exam.exam_id, 1, "A")
    await _seed_response(session, p1.id, q.id, exam.exam_id, "A")  # correct
    await _seed_response(session, p2.id, q.id, exam.exam_id, "B")  # wrong

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    results = await svc.calculate_all_scores(exam.exam_id)

    assert len(results) == 2
    assert results[0].final_score >= results[1].final_score
    assert results[0].participant_name == "Alice"


# ------------------------------------------------------------------ #
# calculate_exam_statistics
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_exam_statistics_basic(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 9.4 - aggregate statistics are computed correctly."""
    exam = await _seed_exam(session, exam_repo, symbolic_note=100)
    p1 = await _seed_participant(session, exam.exam_id, nome="A")
    p2 = await _seed_participant(session, exam.exam_id, nome="B")
    q = await _seed_question(session, exam.exam_id, 1, "A")
    await _seed_response(session, p1.id, q.id, exam.exam_id, "A")  # 100
    await _seed_response(session, p2.id, q.id, exam.exam_id, "B")  # 0

    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    stats = await svc.calculate_exam_statistics(exam.exam_id)

    assert stats.total_participants == 2
    assert stats.highest_score == pytest.approx(100.0)
    assert stats.lowest_score == pytest.approx(0.0)
    assert stats.average_score == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_participant_not_found_raises(exam_repo, participant_repo, question_repo, response_repo):
    svc = make_service(exam_repo, participant_repo, question_repo, response_repo)
    with pytest.raises(ValueError, match="not found"):
        await svc.calculate_participant_score(9999, 1)

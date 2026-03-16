"""
Unit tests for ExamHistoryService.
Requirements: 8.1-8.5, 9.1-9.7
"""
import pytest

from backend.entities.exam import Exam
from backend.entities.participante import Participante
from backend.entities.questao import Questao
from backend.entities.resposta import Resposta
from backend.services.exam_history_service import ExamHistoryService
from backend.services.score_calculator_service import ScoreCalculatorService


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def make_score_service(exam_repo, participant_repo, question_repo, response_repo):
    return ScoreCalculatorService(
        exam_repo=exam_repo,
        participant_repo=participant_repo,
        question_repo=question_repo,
        response_repo=response_repo,
    )


def make_history_service(exam_repo, participant_repo, question_repo, response_repo):
    score_svc = make_score_service(exam_repo, participant_repo, question_repo, response_repo)
    return ExamHistoryService(
        exam_repo=exam_repo,
        participant_repo=participant_repo,
        question_repo=question_repo,
        response_repo=response_repo,
        score_service=score_svc,
    )


async def _seed_exam(session, name="Exam", symbolic_note=100):
    exam = Exam(exam_name=name, questions_numbers=2, symbolic_note=symbolic_note, status="completed")
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
# list_exams
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_list_exams_returns_summary(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 8.1, 8.2 - list includes participant and question counts."""
    exam = await _seed_exam(session, "Prova A")
    await _seed_participant(session, exam.exam_id, "Alice")
    await _seed_participant(session, exam.exam_id, "Bob")
    await _seed_question(session, exam.exam_id, 1, "A")

    svc = make_history_service(exam_repo, participant_repo, question_repo, response_repo)
    results = await svc.list_exams()

    assert len(results) == 1
    assert results[0]["exam_name"] == "Prova A"
    assert results[0]["total_participants"] == 2
    assert results[0]["total_questions"] == 1


@pytest.mark.asyncio
async def test_list_exams_name_filter(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 8.7 - partial name search."""
    await _seed_exam(session, "Matemática 2024")
    await _seed_exam(session, "Português 2024")

    svc = make_history_service(exam_repo, participant_repo, question_repo, response_repo)
    results = await svc.list_exams(name_filter="Matemática")

    assert len(results) == 1
    assert "Matemática" in results[0]["exam_name"]


# ------------------------------------------------------------------ #
# get_exam_details
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_get_exam_details_includes_participants_and_questions(
    session, exam_repo, participant_repo, question_repo, response_repo
):
    """Req 8.3, 8.4, 8.5 - details include participants and questions."""
    exam = await _seed_exam(session)
    await _seed_participant(session, exam.exam_id, "Alice")
    await _seed_question(session, exam.exam_id, 1, "A")

    svc = make_history_service(exam_repo, participant_repo, question_repo, response_repo)
    details = await svc.get_exam_details(exam.exam_id)

    assert details["exam"].exam_id == exam.exam_id
    assert len(details["participants"]) == 1
    assert len(details["questions"]) == 1


@pytest.mark.asyncio
async def test_get_exam_details_not_found_raises(exam_repo, participant_repo, question_repo, response_repo):
    svc = make_history_service(exam_repo, participant_repo, question_repo, response_repo)
    with pytest.raises(ValueError, match="not found"):
        await svc.get_exam_details(9999)


# ------------------------------------------------------------------ #
# get_exam_results
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_get_exam_results_ranked(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 9.1, 9.2 - results are ranked by score."""
    exam = await _seed_exam(session, symbolic_note=100)
    p1 = await _seed_participant(session, exam.exam_id, "Alice")
    p2 = await _seed_participant(session, exam.exam_id, "Bob")
    q = await _seed_question(session, exam.exam_id, 1, "A")
    await _seed_response(session, p1.id, q.id, exam.exam_id, "A")  # correct
    await _seed_response(session, p2.id, q.id, exam.exam_id, "B")  # wrong

    svc = make_history_service(exam_repo, participant_repo, question_repo, response_repo)
    results = await svc.get_exam_results(exam.exam_id)

    assert len(results) == 2
    assert results[0].final_score > results[1].final_score
    assert results[0].participant_name == "Alice"


@pytest.mark.asyncio
async def test_get_exam_results_not_found_raises(exam_repo, participant_repo, question_repo, response_repo):
    svc = make_history_service(exam_repo, participant_repo, question_repo, response_repo)
    with pytest.raises(ValueError, match="not found"):
        await svc.get_exam_results(9999)


# ------------------------------------------------------------------ #
# get_question_statistics
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_question_statistics_correct_rate(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 9.6 - correct answer rate per question."""
    exam = await _seed_exam(session, symbolic_note=100)
    p1 = await _seed_participant(session, exam.exam_id, "Alice")
    p2 = await _seed_participant(session, exam.exam_id, "Bob")
    q = await _seed_question(session, exam.exam_id, 1, "A")
    await _seed_response(session, p1.id, q.id, exam.exam_id, "A")  # correct
    await _seed_response(session, p2.id, q.id, exam.exam_id, "B")  # wrong

    svc = make_history_service(exam_repo, participant_repo, question_repo, response_repo)
    stats = await svc.get_question_statistics(exam.exam_id)

    assert len(stats) == 1
    assert stats[0]["correct_rate_percentage"] == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_question_statistics_sorted_by_difficulty(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 9.7 - hardest questions (lowest rate) appear first."""
    exam = await _seed_exam(session, symbolic_note=100)
    p = await _seed_participant(session, exam.exam_id, "Alice")
    q_easy = await _seed_question(session, exam.exam_id, 1, "A")
    q_hard = await _seed_question(session, exam.exam_id, 2, "B")
    await _seed_response(session, p.id, q_easy.id, exam.exam_id, "A")  # correct
    await _seed_response(session, p.id, q_hard.id, exam.exam_id, "C")  # wrong

    svc = make_history_service(exam_repo, participant_repo, question_repo, response_repo)
    stats = await svc.get_question_statistics(exam.exam_id)

    # Hardest (0% rate) should be first
    assert stats[0]["correct_rate_percentage"] <= stats[-1]["correct_rate_percentage"]


# ------------------------------------------------------------------ #
# export_results_to_excel
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_export_results_to_excel_returns_bytes(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 9.5 - export returns non-empty bytes."""
    exam = await _seed_exam(session)
    p = await _seed_participant(session, exam.exam_id, "Alice")
    q = await _seed_question(session, exam.exam_id, 1, "A")
    await _seed_response(session, p.id, q.id, exam.exam_id, "A")

    svc = make_history_service(exam_repo, participant_repo, question_repo, response_repo)
    data = await svc.export_results_to_excel(exam.exam_id)

    assert isinstance(data, bytes)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_export_results_not_found_raises(exam_repo, participant_repo, question_repo, response_repo):
    svc = make_history_service(exam_repo, participant_repo, question_repo, response_repo)
    with pytest.raises(ValueError, match="not found"):
        await svc.export_results_to_excel(9999)

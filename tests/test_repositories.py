"""
Unit tests for async repository implementations.
Requirements: 1.1, 2.1, 3.1, 4.1, 3.6, 6.8
"""
import pytest

from backend.entities.exam import Exam
from backend.entities.participante import Participante
from backend.entities.questao import Questao
from backend.entities.resposta import Resposta


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

async def _make_exam(session, name="Test Exam"):
    exam = Exam(exam_name=name, questions_numbers=5, symbolic_note=100, status="draft")
    session.add(exam)
    await session.flush()
    await session.refresh(exam)
    return exam


async def _make_participant(session, exam_id, nome="Alice"):
    p = Participante(exam_id=exam_id, nome=nome, presente=False, essay_points=0.0)
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p


async def _make_question(session, exam_id, numero=1, correct_answer="A", peso=1):
    q = Questao(exam_id=exam_id, numero=numero, peso=peso, question_correct_answer=correct_answer)
    session.add(q)
    await session.flush()
    await session.refresh(q)
    return q


async def _make_response(session, user_id, quest_id, exam_id, marked="A"):
    r = Resposta(user_id=user_id, quest_id=quest_id, exam_id=exam_id, marked_answer=marked)
    session.add(r)
    await session.flush()
    await session.refresh(r)
    return r


# ------------------------------------------------------------------ #
# AsyncExamRepository
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_exam_create_and_get(session, exam_repo):
    exam = Exam(exam_name="Prova", questions_numbers=10, symbolic_note=1000, status="draft")
    created = await exam_repo.create(exam)
    assert created.exam_id is not None

    fetched = await exam_repo.get_by_id(created.exam_id)
    assert fetched is not None
    assert fetched.exam_name == "Prova"


@pytest.mark.asyncio
async def test_exam_get_by_id_not_found(exam_repo):
    result = await exam_repo.get_by_id(9999)
    assert result is None


@pytest.mark.asyncio
async def test_exam_get_all(session, exam_repo):
    await _make_exam(session, "E1")
    await _make_exam(session, "E2")
    all_exams = await exam_repo.get_all()
    assert len(all_exams) == 2


@pytest.mark.asyncio
async def test_exam_update(session, exam_repo):
    exam = await _make_exam(session)
    exam.exam_name = "Updated"
    updated = await exam_repo.update(exam)
    assert updated.exam_name == "Updated"


@pytest.mark.asyncio
async def test_exam_delete(session, exam_repo):
    exam = await _make_exam(session)
    result = await exam_repo.delete(exam.exam_id)
    assert result is True
    assert await exam_repo.get_by_id(exam.exam_id) is None


@pytest.mark.asyncio
async def test_exam_filter_by_status(session, exam_repo):
    exam = await _make_exam(session)
    exam.status = "in_progress"
    await exam_repo.update(exam)
    await _make_exam(session, "Draft Exam")  # stays draft

    results = await exam_repo.filter_by_status("in_progress")
    assert len(results) == 1
    assert results[0].status == "in_progress"


@pytest.mark.asyncio
async def test_exam_search_by_name(session, exam_repo):
    await _make_exam(session, "Matemática 2024")
    await _make_exam(session, "Português 2024")

    results = await exam_repo.search_by_name("Matemática")
    assert len(results) == 1
    assert "Matemática" in results[0].exam_name


# ------------------------------------------------------------------ #
# AsyncParticipantRepository
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_participant_create_and_get(session, exam_repo, participant_repo):
    exam = await _make_exam(session)
    p = Participante(exam_id=exam.exam_id, nome="Bob", presente=False, essay_points=0.0)
    created = await participant_repo.create(p)
    assert created.id is not None

    fetched = await participant_repo.get_by_id(created.id)
    assert fetched.nome == "Bob"


@pytest.mark.asyncio
async def test_participant_get_by_exam_id(session, exam_repo, participant_repo):
    exam = await _make_exam(session)
    await _make_participant(session, exam.exam_id, "Alice")
    await _make_participant(session, exam.exam_id, "Bob")

    results = await participant_repo.get_by_exam_id(exam.exam_id)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_participant_create_bulk(session, exam_repo, participant_repo):
    exam = await _make_exam(session)
    participants = [
        Participante(exam_id=exam.exam_id, nome=f"P{i}", presente=False, essay_points=0.0)
        for i in range(5)
    ]
    created = await participant_repo.create_bulk(participants)
    assert len(created) == 5
    assert all(p.id is not None for p in created)


@pytest.mark.asyncio
async def test_participant_update(session, exam_repo, participant_repo):
    exam = await _make_exam(session)
    p = await _make_participant(session, exam.exam_id)
    p.presente = True
    updated = await participant_repo.update(p)
    assert updated.presente is True


@pytest.mark.asyncio
async def test_participant_delete(session, exam_repo, participant_repo):
    exam = await _make_exam(session)
    p = await _make_participant(session, exam.exam_id)
    result = await participant_repo.delete(p.id)
    assert result is True
    assert await participant_repo.get_by_id(p.id) is None


# ------------------------------------------------------------------ #
# AsyncQuestionRepository
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_question_create_and_get(session, exam_repo, question_repo):
    exam = await _make_exam(session)
    q = Questao(exam_id=exam.exam_id, numero=1, peso=2, question_correct_answer="B")
    created = await question_repo.create(q)
    assert created.id is not None

    fetched = await question_repo.get_by_id(created.id)
    assert fetched.question_correct_answer == "B"


@pytest.mark.asyncio
async def test_question_get_by_exam_id(session, exam_repo, question_repo):
    exam = await _make_exam(session)
    await _make_question(session, exam.exam_id, 1)
    await _make_question(session, exam.exam_id, 2)

    results = await question_repo.get_by_exam_id(exam.exam_id)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_question_create_bulk(session, exam_repo, question_repo):
    exam = await _make_exam(session)
    questions = [
        Questao(exam_id=exam.exam_id, numero=i, peso=1, question_correct_answer="A")
        for i in range(1, 6)
    ]
    created = await question_repo.create_bulk(questions)
    assert len(created) == 5


@pytest.mark.asyncio
async def test_question_get_by_exam_and_number(session, exam_repo, question_repo):
    exam = await _make_exam(session)
    await _make_question(session, exam.exam_id, 3, "C")

    result = await question_repo.get_by_exam_and_number(exam.exam_id, 3)
    assert result is not None
    assert result.numero == 3


@pytest.mark.asyncio
async def test_question_delete(session, exam_repo, question_repo):
    exam = await _make_exam(session)
    q = await _make_question(session, exam.exam_id)
    result = await question_repo.delete(q.id)
    assert result is True
    assert await question_repo.get_by_id(q.id) is None


# ------------------------------------------------------------------ #
# AsyncResponseRepository
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_response_create_and_get(session, exam_repo, participant_repo, question_repo, response_repo):
    exam = await _make_exam(session)
    p = await _make_participant(session, exam.exam_id)
    q = await _make_question(session, exam.exam_id)
    r = Resposta(user_id=p.id, quest_id=q.id, exam_id=exam.exam_id, marked_answer="A")
    created = await response_repo.create(r)
    assert created.id is not None

    fetched = await response_repo.get_by_id(created.id)
    assert fetched.marked_answer == "A"


@pytest.mark.asyncio
async def test_response_upsert_creates_new(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 6.8 - upsert creates when no existing response."""
    exam = await _make_exam(session)
    p = await _make_participant(session, exam.exam_id)
    q = await _make_question(session, exam.exam_id)
    r = Resposta(user_id=p.id, quest_id=q.id, exam_id=exam.exam_id, marked_answer="B")
    created = await response_repo.create_or_update(r)
    assert created.id is not None
    assert created.marked_answer == "B"


@pytest.mark.asyncio
async def test_response_upsert_updates_existing(session, exam_repo, participant_repo, question_repo, response_repo):
    """Req 6.8 - upsert updates when response already exists."""
    exam = await _make_exam(session)
    p = await _make_participant(session, exam.exam_id)
    q = await _make_question(session, exam.exam_id)
    await _make_response(session, p.id, q.id, exam.exam_id, "A")

    # Now upsert with different answer
    r_new = Resposta(user_id=p.id, quest_id=q.id, exam_id=exam.exam_id, marked_answer="C")
    updated = await response_repo.create_or_update(r_new)
    assert updated.marked_answer == "C"

    # Verify only one response exists
    all_responses = await response_repo.get_by_exam_id(exam.exam_id)
    assert len(all_responses) == 1


@pytest.mark.asyncio
async def test_response_get_by_participant_and_exam(session, exam_repo, participant_repo, question_repo, response_repo):
    exam = await _make_exam(session)
    p = await _make_participant(session, exam.exam_id)
    q1 = await _make_question(session, exam.exam_id, 1)
    q2 = await _make_question(session, exam.exam_id, 2)
    await _make_response(session, p.id, q1.id, exam.exam_id, "A")
    await _make_response(session, p.id, q2.id, exam.exam_id, "B")

    results = await response_repo.get_by_participant_and_exam(p.id, exam.exam_id)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_response_delete(session, exam_repo, participant_repo, question_repo, response_repo):
    exam = await _make_exam(session)
    p = await _make_participant(session, exam.exam_id)
    q = await _make_question(session, exam.exam_id)
    r = await _make_response(session, p.id, q.id, exam.exam_id, "A")

    result = await response_repo.delete(r.id)
    assert result is True
    assert await response_repo.get_by_id(r.id) is None

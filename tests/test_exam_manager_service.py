"""
Unit tests for ExamManagerService.
Requirements: 1.1, 1.2, 1.3, 1.6, 1.7, 17.1-17.5
"""
import pytest
from datetime import datetime

from backend.entities.exam import Exam
from backend.entities.participante import Participante
from backend.schemas.exam import ExamCreate, ExamUpdate
from backend.schemas.participante import ParticipantCreate
from backend.services.exam_manager_service import ExamManagerService


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def make_service(exam_repo, participant_repo):
    return ExamManagerService(exam_repo=exam_repo, participant_repo=participant_repo)


# ------------------------------------------------------------------ #
# create_exam
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_create_exam_returns_response(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    data = ExamCreate(exam_name="Prova 1", questions_numbers=10, symbolic_note=100)
    result = await svc.create_exam(data)

    assert result.exam_id is not None
    assert result.exam_name == "Prova 1"
    assert result.questions_numbers == 10
    assert result.symbolic_note == 100
    assert result.status == "draft"


@pytest.mark.asyncio
async def test_create_exam_unique_ids(exam_repo, participant_repo):
    """Each exam gets a unique exam_id. Req 1.2"""
    svc = make_service(exam_repo, participant_repo)
    a = await svc.create_exam(ExamCreate(exam_name="A", questions_numbers=5, symbolic_note=50))
    b = await svc.create_exam(ExamCreate(exam_name="B", questions_numbers=5, symbolic_note=50))
    assert a.exam_id != b.exam_id


@pytest.mark.asyncio
async def test_create_exam_default_symbolic_note(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    result = await svc.create_exam(ExamCreate(exam_name="X", questions_numbers=1))
    assert result.symbolic_note == 1000


# ------------------------------------------------------------------ #
# get_exam
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_get_exam_found(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    created = await svc.create_exam(ExamCreate(exam_name="Test", questions_numbers=3))
    fetched = await svc.get_exam(created.exam_id)
    assert fetched.exam_id == created.exam_id
    assert fetched.exam_name == "Test"


@pytest.mark.asyncio
async def test_get_exam_not_found_raises(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    with pytest.raises(ValueError, match="not found"):
        await svc.get_exam(9999)


# ------------------------------------------------------------------ #
# update_exam
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_update_exam_name(exam_repo, participant_repo):
    """Req 1.6 - administrators can update exam configuration fields."""
    svc = make_service(exam_repo, participant_repo)
    created = await svc.create_exam(ExamCreate(exam_name="Old", questions_numbers=5))
    updated = await svc.update_exam(created.exam_id, ExamUpdate(exam_name="New"))
    assert updated.exam_name == "New"
    assert updated.questions_numbers == 5  # unchanged


@pytest.mark.asyncio
async def test_update_exam_status(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    created = await svc.create_exam(ExamCreate(exam_name="E", questions_numbers=2))
    updated = await svc.update_exam(created.exam_id, ExamUpdate(status="in_progress"))
    assert updated.status == "in_progress"


@pytest.mark.asyncio
async def test_update_exam_not_found_raises(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    with pytest.raises(ValueError, match="not found"):
        await svc.update_exam(9999, ExamUpdate(exam_name="X"))


# ------------------------------------------------------------------ #
# delete_exam
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_delete_exam_success(exam_repo, participant_repo):
    """Req 1.7 - deleting an exam removes it."""
    svc = make_service(exam_repo, participant_repo)
    created = await svc.create_exam(ExamCreate(exam_name="Del", questions_numbers=1))
    result = await svc.delete_exam(created.exam_id)
    assert result is True
    with pytest.raises(ValueError):
        await svc.get_exam(created.exam_id)


@pytest.mark.asyncio
async def test_delete_exam_not_found_raises(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    with pytest.raises(ValueError, match="not found"):
        await svc.delete_exam(9999)


# ------------------------------------------------------------------ #
# list_exams
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_list_exams_returns_all(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    await svc.create_exam(ExamCreate(exam_name="E1", questions_numbers=1))
    await svc.create_exam(ExamCreate(exam_name="E2", questions_numbers=2))
    exams = await svc.list_exams()
    assert len(exams) == 2


@pytest.mark.asyncio
async def test_list_exams_filter_by_status(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    e = await svc.create_exam(ExamCreate(exam_name="Active", questions_numbers=1))
    await svc.update_exam(e.exam_id, ExamUpdate(status="in_progress"))
    await svc.create_exam(ExamCreate(exam_name="Draft", questions_numbers=1))

    active = await svc.list_exams(status="in_progress")
    assert len(active) == 1
    assert active[0].exam_name == "Active"


@pytest.mark.asyncio
async def test_list_exams_search_by_name(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    await svc.create_exam(ExamCreate(exam_name="Matemática 2024", questions_numbers=1))
    await svc.create_exam(ExamCreate(exam_name="Português 2024", questions_numbers=1))

    results = await svc.list_exams(name="Matemática")
    assert len(results) == 1
    assert "Matemática" in results[0].exam_name


# ------------------------------------------------------------------ #
# add_participant_to_exam
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_add_participant_creates_record(exam_repo, participant_repo):
    """Req 17.4 - participant is created and associated with exam."""
    svc = make_service(exam_repo, participant_repo)
    exam = await svc.create_exam(ExamCreate(exam_name="E", questions_numbers=1))
    p = await svc.add_participant_to_exam(exam.exam_id, ParticipantCreate(nome="Alice", exam_id=exam.exam_id))

    assert p.id is not None
    assert p.nome == "Alice"
    assert p.exam_id == exam.exam_id
    assert p.presente is False  # Req 17.5


@pytest.mark.asyncio
async def test_add_participant_strips_whitespace(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    exam = await svc.create_exam(ExamCreate(exam_name="E", questions_numbers=1))
    p = await svc.add_participant_to_exam(exam.exam_id, ParticipantCreate(nome="  Bob  ", exam_id=exam.exam_id))
    assert p.nome == "Bob"


@pytest.mark.asyncio
async def test_add_participant_empty_name_raises(exam_repo, participant_repo):
    """Req 17.3 - name must not be empty."""
    svc = make_service(exam_repo, participant_repo)
    exam = await svc.create_exam(ExamCreate(exam_name="E", questions_numbers=1))
    with pytest.raises(ValueError, match="empty"):
        await svc.add_participant_to_exam(exam.exam_id, ParticipantCreate(nome="   ", exam_id=exam.exam_id))


@pytest.mark.asyncio
async def test_add_participant_exam_not_found_raises(exam_repo, participant_repo):
    svc = make_service(exam_repo, participant_repo)
    with pytest.raises(ValueError, match="not found"):
        await svc.add_participant_to_exam(9999, ParticipantCreate(nome="X", exam_id=9999))

from pydantic import BaseModel, Field
from typing import Optional


class ParticipantBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)


class ParticipantCreate(ParticipantBase):
    exam_id: int


class ParticipantAddRequest(ParticipantBase):
    """Request body for adding a participant via POST /exams/{exam_id}/participants.
    exam_id is taken from the path parameter, not the body."""
    pass


class ParticipantUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    presente: Optional[bool] = None
    essay_points: Optional[float] = Field(None, ge=0)


class ParticipantResponse(ParticipantBase):
    id: int
    exam_id: int
    presente: bool
    essay_points: float

    class Config:
        from_attributes = True

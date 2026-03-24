from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExamBase(BaseModel):
    exam_name: str = Field(..., min_length=1, max_length=255)
    questions_numbers: int = Field(..., gt=0)
    symbolic_note: int = Field(1000, gt=0)


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    exam_name: Optional[str] = Field(None, min_length=1, max_length=255)
    questions_numbers: Optional[int] = Field(None, gt=0)
    symbolic_note: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(None, pattern="^(draft|in_progress|completed)$")
    ended_at: Optional[datetime] = None


class ExamResponse(ExamBase):
    exam_id: int
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None
    status: str

    class Config:
        from_attributes = True

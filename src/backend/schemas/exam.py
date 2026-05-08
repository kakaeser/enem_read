from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ExamBase(BaseModel):
    exam_name: str = Field(..., min_length=1, max_length=255)
    questions_numbers: int = Field(..., gt=0)
    symbolic_note: int = Field(1000, gt=0)


class ExamCreate(ExamBase):
    """
    weight_mode:
      "default"       — all questions peso=1
      "even_questions"— even-numbered questions (2,4,6…) get peso=2, others peso=1
      "odd_questions" — odd-numbered questions (1,3,5…) get peso=2, others peso=1
      "custom"        — questions listed in heavy_questions get peso=2, others peso=1
    heavy_questions: list of question numbers that should have peso=2 (only for "custom")
    """
    weight_mode: str = Field("default", pattern="^(default|even_questions|odd_questions|custom)$")
    heavy_questions: Optional[List[int]] = None  # question numbers with peso=2


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

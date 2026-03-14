from pydantic import BaseModel, Field
from typing import Optional


class QuestionBase(BaseModel):
    numero: int = Field(..., gt=0)
    peso: int = Field(1, gt=0, le=100)
    question_correct_answer: Optional[str] = Field(None, pattern="^[A-Z0-9]$")


class QuestionCreate(QuestionBase):
    exam_id: int


class QuestionUpdate(BaseModel):
    peso: Optional[int] = Field(None, gt=0, le=100)
    question_correct_answer: Optional[str] = Field(None, pattern="^[A-Z0-9]$")


class QuestionResponse(QuestionBase):
    id: int
    exam_id: int

    class Config:
        from_attributes = True

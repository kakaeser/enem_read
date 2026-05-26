from pydantic import BaseModel, Field
from typing import Optional


class ResponseBase(BaseModel):
    marked_answer: Optional[str] = Field(None, pattern="^[A-Z0-9]$")


class ResponseCreate(ResponseBase):
    user_id: int
    quest_id: int
    exam_id: int
    confidence_score: Optional[float] = Field(None, ge=0, le=100)


class ResponseUpdate(BaseModel):
    marked_answer: Optional[str] = Field(None, pattern="^[A-Z0-9]$")
    confidence_score: Optional[float] = Field(None, ge=0, le=100)
    manually_reviewed: Optional[bool] = None


class ResponseResponse(ResponseBase):
    id: int
    user_id: int
    quest_id: int
    exam_id: int
    confidence_score: Optional[float]
    manually_reviewed: bool

    class Config:
        from_attributes = True

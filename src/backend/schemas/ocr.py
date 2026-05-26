from pydantic import BaseModel, Field
from typing import List, Optional


class ExtractedAnswer(BaseModel):
    question_number: int = Field(..., gt=0)
    answer: str
    confidence: float = Field(..., ge=0, le=100)


class AnswerKeyResult(BaseModel):
    exam_id: int
    extracted_answers: List[ExtractedAnswer]
    avg_confidence: float
    flagged_count: int
    success: bool
    error_message: Optional[str] = None


class AnswerSheetResult(BaseModel):
    participant_id: int
    exam_id: int
    extracted_answers: List[ExtractedAnswer]
    avg_confidence: float
    flagged_count: int
    success: bool
    error_message: Optional[str] = None

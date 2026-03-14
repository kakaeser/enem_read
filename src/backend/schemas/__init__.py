from backend.schemas.exam import ExamCreate, ExamUpdate, ExamResponse
from backend.schemas.questao import QuestionCreate, QuestionUpdate, QuestionResponse
from backend.schemas.participante import ParticipantCreate, ParticipantUpdate, ParticipantResponse
from backend.schemas.resposta import ResponseCreate, ResponseUpdate, ResponseResponse
from backend.schemas.ocr import ExtractedAnswer, AnswerKeyResult, AnswerSheetResult
from backend.schemas.scoring import ScoreBreakdown, ExamStatistics

__all__ = [
    "ExamCreate", "ExamUpdate", "ExamResponse",
    "QuestionCreate", "QuestionUpdate", "QuestionResponse",
    "ParticipantCreate", "ParticipantUpdate", "ParticipantResponse",
    "ResponseCreate", "ResponseUpdate", "ResponseResponse",
    "ExtractedAnswer", "AnswerKeyResult", "AnswerSheetResult",
    "ScoreBreakdown", "ExamStatistics",
]

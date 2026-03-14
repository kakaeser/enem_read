from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    participant_id: int
    participant_name: str
    raw_score: float
    total_possible_score: float
    normalized_score: float
    essay_points: float
    final_score: float
    correct_count: int
    total_questions: int
    accuracy_percentage: float


class ExamStatistics(BaseModel):
    exam_id: int
    total_participants: int
    participants_with_submissions: int
    average_score: float
    median_score: float
    highest_score: float
    lowest_score: float
    std_deviation: float

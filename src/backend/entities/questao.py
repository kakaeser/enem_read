from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index
from backend.config.base import Base
from sqlalchemy.orm import relationship


class Questao(Base):
    __tablename__ = "questoes"
    __table_args__ = (
        UniqueConstraint("exam_id", "numero", name="uq_exam_question_number"),
        Index("idx_exam_questions", "exam_id"),
    )

    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.exam_id"), nullable=False)
    numero = Column(Integer, nullable=False)
    peso = Column(Integer, default=1)
    question_correct_answer = Column(String(10), nullable=True)  # A, B, C, D, E, etc.

    # Relationships
    exam = relationship("Exam", back_populates="questions")
    respostas = relationship(
        "Resposta",
        back_populates="questao",
        cascade="all, delete-orphan"
    )

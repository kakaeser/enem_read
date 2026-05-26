from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, UniqueConstraint, Index
from backend.config.base import Base
from sqlalchemy.orm import relationship


class Resposta(Base):
    __tablename__ = "resultados"
    __table_args__ = (
        UniqueConstraint("user_id", "quest_id", name="uq_usuario_questao"),
        Index("idx_exam_responses", "exam_id"),
        Index("idx_participant_responses", "user_id"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("participantes.id"), nullable=False)
    quest_id = Column(Integer, ForeignKey("questoes.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.exam_id"), nullable=False)
    marked_answer = Column(String(10), nullable=True)  # A, B, C, D, E, etc.
    confidence_score = Column(Float, nullable=True)  # 0-100
    manually_reviewed = Column(Boolean, default=False)

    # Relationships
    participante = relationship("Participante", back_populates="respostas")
    questao = relationship("Questao", back_populates="respostas")
    exam = relationship("Exam", back_populates="responses")
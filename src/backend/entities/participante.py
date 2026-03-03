from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Index
from backend.config.base import Base
from sqlalchemy.orm import relationship


class Participante(Base):
    __tablename__ = "participantes"
    __table_args__ = (
        Index("idx_exam_participants", "exam_id"),
    )

    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.exam_id"), nullable=False)
    nome = Column(String(255), nullable=False)
    presente = Column(Boolean, default=False)
    essay_points = Column(Float, default=0.0)

    # Relationships
    exam = relationship("Exam", back_populates="participants")
    respostas = relationship("Resposta", back_populates="participante", cascade="all, delete-orphan")
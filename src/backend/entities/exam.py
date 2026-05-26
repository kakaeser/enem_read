from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from backend.config.base import Base
from datetime import datetime


class Exam(Base):
    __tablename__ = "exams"

    exam_id = Column(Integer, primary_key=True)
    exam_name = Column(String(255), nullable=False)
    questions_numbers = Column(Integer, nullable=False)
    symbolic_note = Column(Integer, nullable=False, default=1000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True, default=None)
    status = Column(String(50), default="draft")  # draft, in_progress, completed

    # Relationships
    questions = relationship("Questao", back_populates="exam", cascade="all, delete-orphan")
    participants = relationship("Participante", back_populates="exam", cascade="all, delete-orphan")
    responses = relationship("Resposta", back_populates="exam", cascade="all, delete-orphan")

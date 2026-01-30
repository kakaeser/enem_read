from sqlalchemy import Column, Integer, String, Boolean
from backend.config.base import Base
from sqlalchemy.orm import relationship

class Participante(Base):
    __tablename__ = "participantes"

    id = Column(Integer, primary_key= True)
    nome = Column(String)
    presente = Column(Boolean, default = False)

    respostas = relationship("Resposta", back_populates="participante", cascade="all, delete-orphan")
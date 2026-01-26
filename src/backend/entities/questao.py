from sqlalchemy import Column, Integer
from backend.config.base import Base
from sqlalchemy.orm import relationship

class Questao(Base):
    __tablename__ = "questoes"

    id = Column(Integer, primary_key=True)
    numero = Column(Integer, nullable=False)
    peso = Column(Integer, default=1)

    respostas = relationship(
        "Resposta",
        back_populates="questao",
        cascade="all, delete-orphan"
    )

from sqlalchemy import Column, Integer, Boolean, ForeignKey, UniqueConstraint
from backend.config.base import Base
from sqlalchemy.orm import relationship

class Resposta(Base):
    __tablename__ = "resultados"
    __table_args__ = (UniqueConstraint("user_id", "quest_id", name="uq_usuario_questao"),)

    id = Column(Integer, primary_key= True)
    user_id = Column(Integer, ForeignKey("participantes.id"), nullable= False)
    quest_id = Column(Integer, ForeignKey("questoes.id"), nullable= False)
    acertou = Column(Boolean, default= False)

    participante = relationship("Participante",back_populates="respostas")
    questao = relationship("Questao",back_populates="respostas")
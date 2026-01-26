from backend.config.connection import DBConnectionHandler
from backend.config.base import Base

# IMPORTANTE: importar TODAS as entidades
from backend.entities.participante import Participante
from backend.entities.questao import Questao
from backend.entities.resposta import Resposta


def init_db():
    db = DBConnectionHandler()
    engine = db.get_engine()
    Base.metadata.create_all(engine)

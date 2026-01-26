from entities.participante import Participante
from config.connection import DBConnectionHandler


class ParticipanteRepo:

    def listar_ordem_alfabetica(self):
        with DBConnectionHandler() as db:
            data = db.session.query(Participante).order_by(Participante.nome).all()
        return data
    
    def listar_presentes(self):
        with DBConnectionHandler() as db:
            data = db.session.query(Participante).filter(Participante.presente == True).all()
        return data
    
    def buscar_por_id(self, id:int):
        with DBConnectionHandler() as db:
            data = db.session.query(Participante).filter(Participante.id == id).first()
        return data
    
    def marcar_presenca(self, user_id:int,mark:int):
        presente : bool
        if mark == 0:
            presente = False
        elif mark == 1:
            presente = True
        else:
            return False
        with DBConnectionHandler() as db:
            participante = (db.session.query(Participante).filter(Participante.id == user_id).first())
            if not participante:
                return False
            
            participante.presente = presente
            return True
from backend.entities.participante import Participante
from backend.config.connection import DBConnectionHandler


class ParticipanteRepo:

    def listar_ordem_alfabetica(self):
        with DBConnectionHandler() as db:
            participantes = db.session.query(Participante).order_by(Participante.nome).all()
            # transforma cada objeto em dict dentro da sessão
            return [
                {
                    "id": p.id,
                    "nome": p.nome,
                    "email": p.email,
                    "cpf": p.cpf,
                    "presente": p.presente
                }
                for p in participantes
            ] or []
    def listar_presentes(self):
        with DBConnectionHandler() as db:
            participantes = (
                db.session
                .query(Participante)
                .filter(Participante.presente == True)
                .all()
            )

            return [
                {
                    "id": p.id,
                    "nome": p.nome
                }
                for p in participantes
            ]
    
    def buscar_por_id(self, id:int):
        with DBConnectionHandler() as db:
            data = db.session.query(Participante).filter(Participante.id == id).first()
            return [
                {
                    "id": p.id,
                    "nome": p.nome,
                    "email": p.email,
                    "cpf": p.cpf,
                    "presente": p.presente
                }
                for p in data
            ] or []
    
    def buscar_por_nome(self, nome: str):
        with DBConnectionHandler() as db:
            data = db.session.query(Participante).filter(Participante.nome == nome).first()
            return [
                {
                    "id": p.id,
                    "nome": p.nome,
                    "email": p.email,
                    "cpf": p.cpf,
                    "presente": p.presente
                }
                for p in data
            ] or []
    
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
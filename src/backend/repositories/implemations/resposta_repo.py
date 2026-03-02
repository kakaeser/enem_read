from backend.entities.resposta import Resposta
from backend.config.connection import DBConnectionHandler

class RespostaRepo:
    def add_resposta(self, p_id, q_id):
        with DBConnectionHandler() as db:
            existe = db.session.query(Resposta).filter(
                Resposta.user_id == p_id,
                Resposta.quest_id == q_id
            ).first()

            if existe:
                return existe
            resposta = Resposta(user_id = p_id,quest_id = q_id)
            db.session.add(resposta)

    def buscar_resposta(self, p_id, q_id):
        with DBConnectionHandler() as db:
            data = db.session.query(Resposta).filter(Resposta.quest_id == q_id, Resposta.user_id == p_id).first()
            return {
                    "id": data.id,
                    "acertou": data.acertou
                } or []
    
    def buscar_respostas_participante(self, p_id):
        with DBConnectionHandler() as db:
            data = db.session.query(Resposta).filter(Resposta.user_id == p_id).all()
            return[
                {
                    "id": i.id,
                    "quest_id": i.quest_id,
                    "acertou": i.acertou
                }
                for i in data
            ] or []
    
    def mudar_acerto(self,  p_id, q_id, novo_acerto):
        mudanca : bool
        if novo_acerto == 1:
            mudanca = True
        else:
            mudanca = False
        with DBConnectionHandler() as db:
            resposta = (db.session.query(Resposta).filter(Resposta.quest_id == q_id, Resposta.user_id == p_id).first())
            if not resposta:
                return False
            
            resposta.acertou = mudanca
            return True

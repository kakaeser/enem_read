from entities.questao import Questao
from config.connection import DBConnectionHandler

class QuestaoRepo:

    def buscar_por_numero(self, numero : int):
        with DBConnectionHandler() as db:
            data = db.session.query(Questao).filter(Questao.numero == numero).first()
        return data

    def listar_ordem_numerica(self):
        with DBConnectionHandler() as db:
            data = db.session.query(Questao).order_by(Questao.numero).all()
        return data
    
    def alterar_peso(self, questao_id: int, peso: int):
        if peso <= 0:
            return False
        
        with DBConnectionHandler() as db:
            questao = (db.session.query(Questao).filter(Questao.id == questao_id).first())
            if not questao:
                return False
            
            questao.peso = peso
            return True
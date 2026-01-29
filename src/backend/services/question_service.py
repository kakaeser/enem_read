from backend.repositories.questao_repo import QuestaoRepo
from backend.repositories.resposta_repo import RespostaRepo
from backend.entities.questao import Questao

class QuestionService:
    def __init__(self):
        self.q_repo = QuestaoRepo()
        self.r_repo = RespostaRepo()

    def criar_questoes(self, numero_questoes, questoes_com_peso):
        questoes = []
        for i in range(1, numero_questoes + 1):
            peso = 2 if i in questoes_com_peso else 1
            questao = Questao(
                numero=i,
                peso=peso
            )
            questoes.append(questao)

        self.q_repo.add_questoes(questoes)

    def string_para_numeros(self,texto: str) -> list[int]:
        return [int(n.strip()) for n in texto.split(",") if n.strip()]
    
    def delete_all(self):
        if self.q_repo.listar_ordem_numerica():
            self.q_repo.delete_questoes()
    
    def buscar_questao(self):
        return self.q_repo.buscar_por_numero(1)

    def listar_questoes(self, p_id):
        data = self.q_repo.listar_ordem_numerica()
        for i in data:
            r = self.r_repo.buscar_resposta(p_id, i["id"])
            if r:
                i["acerto"] = int(r["acertou"])
            else:
                i["acerto"] = 0
        return data
    
    def add_respostas(self, p_id):
        data = self.q_repo.listar_ordem_numerica()
        for i in data:
            self.r_repo.add_resposta(p_id, i["id"])

    def marcar_acertos(self, p_id, q_id, mark: int | bool):
        return self.r_repo.mudar_acerto(p_id, q_id, mark)
    
    def marcar_todos(self, p_id, mark):
        data = self.q_repo.listar_ordem_numerica()
        for i in data:
            self.r_repo.mudar_acerto(p_id, i["id"],mark)

    def calcular_nota_maxima(self):
        questoes = self.q_repo.listar_ordem_numerica()
        return sum(q["peso"] for q in questoes)

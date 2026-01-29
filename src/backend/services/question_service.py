from backend.repositories.participante_repo import ParticipanteRepo
from backend.repositories.questao_repo import QuestaoRepo
from backend.entities.questao import Questao

class QuestionService:
    def __init__(self):
        self.q_repo = QuestaoRepo()

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

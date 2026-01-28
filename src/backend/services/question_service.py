from backend.repositories.participante_repo import ParticipanteRepo
from backend.repositories.questao_repo import QuestaoRepo
from backend.entities.questao import Questao

class QuestionService:
    def __init__(self):
        self.q_repo = QuestaoRepo()

    def criar_questoes(self, numero_questoes, questoes_com_peso):
        for i in range(1, numero_questoes + 1):
            peso = 2 if i in questoes_com_peso else 1
            questao = Questao(
                numero=i,
                peso=peso
            )
        self.q_repo.add_questoes(questao)

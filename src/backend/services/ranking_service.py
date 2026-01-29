from backend.repositories.config_repo import ConfigRepo
from backend.repositories.participante_repo import ParticipanteRepo
from backend.repositories.questao_repo import QuestaoRepo
from backend.repositories.resposta_repo import RespostaRepo

class RankingService:
    def __init__(self):
        self.q_repo = QuestaoRepo()
        self.r_repo = RespostaRepo()
        self.c_repo = ConfigRepo()
        self.p_repo = ParticipanteRepo()

    def config_mani(self, nota_max, nota_simb):
        if self.c_repo.conferir():
            self.c_repo.add(nota_max, nota_simb)
        else:
            self.c_repo.alterar(nota_max, nota_simb)
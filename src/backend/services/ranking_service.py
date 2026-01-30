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
        if not self.c_repo.conferir():
            self.c_repo.add(nota_max, nota_simb)
        else:
            self.c_repo.alterar(nota_max, nota_simb)

    def calcular_nota_maxima(self):
        questoes = self.q_repo.listar_ordem_numerica()
        return sum(q["peso"] for q in questoes)

    def calcular_nota_aluno(self, p_id):
        
        data = self.r_repo.buscar_respostas_participante(p_id)
        questoes = self.q_repo.listar_ordem_numerica()

        pesos = {q["id"]: q["peso"] for q in questoes}
        nota = 0
        for r in data:
            if r["acertou"]:
                nota += pesos.get(r["quest_id"], 0)

        return nota
    
    def gerar_ranking(self):
        ranking = []
        participantes = self.p_repo.listar_presentes()
        config = self.c_repo.get_notas()
        nota_max = config["nota_max"]
        nota_simb = config["nota_simb"]

        for p in participantes:
            respostas = self.r_repo.buscar_respostas_participante(p["id"])

            if not respostas or nota_max <= 0:
                ranking.append({
                    "nome": p["nome"],
                    "nota": "-"
                })
                continue
            nota = self.calcular_nota_aluno(p["id"])
            nota_final = (nota/nota_max) *nota_simb
            ranking.append({"nome": p["nome"], "nota": nota_final})

        ranking.sort(
        key=lambda x: x["nota"] if isinstance(x["nota"], (int, float)) else -1,reverse=True)

        return ranking

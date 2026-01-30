from backend.repositories.participante_repo import ParticipanteRepo
import pandas as pd

class PresenceService:
    def __init__(self):
        self.repo = ParticipanteRepo()

    def listar_nomes(self):
        return self.repo.listar_ordem_alfabetica()  

    def listar_presentes(self):
        return self.repo.listar_presentes()
    
    def marcar_presenca(self, user_id : int, mark :int | bool):
        return self.repo.marcar_presenca(user_id, mark)
    
    def importar_excel(self, caminho_arquivo):
        df = pd.read_excel(caminho_arquivo)

        if "Nome" not in df.columns:
            raise ValueError("O arquivo precisa ter a coluna 'Nome'")
        print("Excel válido")

        nomes = [
            nome.strip()
            for nome in df["Nome"].dropna()
            if nome.strip()
        ]
        self.repo.delete_participantes()
        self.repo.criar_participantes(nomes)

    def delete_participantes(self):
        self.repo.delete_participantes()

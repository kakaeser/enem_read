from backend.repositories.participante_repo import ParticipanteRepo

class PresenceService:
    def __init__(self):
        self.repo = ParticipanteRepo()

    def listar_nomes(self):
        return self.repo.listar_ordem_alfabetica()  

    def listar_presentes(self):
        return self.repo.listar_presentes()
    
    def marcar_presenca(self, user_id : int, mark :int | bool):
        return self.repo.marcar_presenca(user_id, mark)
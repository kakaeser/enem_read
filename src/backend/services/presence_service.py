from backend.repositories.participante_repo import ParticipanteRepo

class PresenceService:
    def __init__(self):
        self.repo = ParticipanteRepo()

    def listar_nomes(self):
        participantes = self.repo.listar_ordem_alfabetica()
        return [
            {
                "id": p.id,
                "nome": p.nome,
                "presente": p.presente
            }
            for p in participantes
        ]
    
    def marcar_presenca(self, user_id : int, mark :int | bool):
        return self.repo.marcar_presenca(user_id, mark)
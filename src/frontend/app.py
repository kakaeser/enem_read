from customtkinter import *
from frontend.lista import Lista
from backend.services.presence_service import PresenceService
from backend.repositories.participante_repo import ParticipanteRepo

set_appearance_mode("Dark")

class App(CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1280x720")
        self.title("Enem da Read")
        self.aluno_selecionado = None
        self.presence_service = PresenceService()

        self.barrahori = CTkFrame(master = self, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0)
        self.barrahori.place(relx = 0.5, rely = 0, relwidth = 1, relheight = 0.05, anchor = "center")

        self.lista = Lista(master = self, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0, presence_service= self.presence_service, on_select_participante= self.selecionar_aluno)
        self.lista.place(relx = 0.19, rely = 0.55, relwidth = 0.3, relheight = 0.7, anchor = "center")
        
        self.barra_nome_lista = CTkFrame(master = self, fg_color=("#EDF0F0", "#0E0D0D"), corner_radius=0)
        self.barra_nome_lista.place(relx = 0.19, rely = 0.175, relwidth = 0.3, relheight = 0.05, anchor = "center")

        self.nome_lista = CTkLabel(master = self.barra_nome_lista, text="Lista de presença")
        self.nome_lista.place(relx = 0.5, rely = 0.5, anchor = "center")

        self.barra_nome_questoes = CTkFrame(master = self, fg_color=("#EDF0F0", "#0E0D0D"), corner_radius=0)
        self.barra_nome_questoes.place(relx = 0.5, rely = 0.175, relwidth = 0.3, relheight = 0.05, anchor = "center")

    
        self.nome_questoes = CTkLabel(master = self.barra_nome_questoes, text=f"Questões do aluno: Não selecionado")
        self.nome_questoes.place(relx = 0.5, rely = 0.5, anchor = "center")
        
        self.questoes = CTkScrollableFrame(master = self, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0)
        self.questoes.place(relx = 0.5, rely = 0.55, relwidth = 0.3, relheight = 0.7, anchor = "center")


        self.barra_nome_rank = CTkFrame(master = self, fg_color=("#EDF0F0", "#0E0D0D"), corner_radius=0)
        self.barra_nome_rank.place(relx = 0.81, rely = 0.175, relwidth = 0.3, relheight = 0.05, anchor = "center")

        self.nome_rank = CTkLabel(master = self.barra_nome_rank, text="Ranking")
        self.nome_rank.place(relx = 0.5, rely = 0.5, anchor = "center")
        
        self.rank = CTkScrollableFrame(master = self, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0)
        self.rank.place(relx = 0.81, rely = 0.55, relwidth = 0.3, relheight = 0.7, anchor = "center")

        
    def selecionar_aluno(self, id, nome):
        presentes = self.presence_service.listar_presentes()

        if any(p["id"] == id for p in presentes):
            self.aluno_selecionado = {"id": id, "nome": nome}
            self.nome_questoes.configure(
                text=f"Questões do aluno: {nome}"
            )
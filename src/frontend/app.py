from customtkinter import *
from frontend.lista import Lista
from frontend.configuracoes import Configuracoes
from frontend.gabarito import Gabarito
from backend.services.presence_service import PresenceService
from backend.services.question_service import QuestionService

set_appearance_mode("Dark")

class App(CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1280x720")
        self.title("Enem da Read")
        self.aluno_selecionado = None
        self.presence_service = PresenceService()
        self.question_service = QuestionService()

        #Inicilização da barra horizontal
        self.barrahori = CTkFrame(master = self, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0)
        self.barrahori.place(relx = 0.5, rely = 0.02, relwidth = 1, relheight = 0.04, anchor = "center")

        self.configuracao = CTkButton(master = self.barrahori, fg_color= "transparent", hover_color= ("#C7C7C7", "#2E2E2E"), text = "Configurações", corner_radius= 0, command = self.abrir_configs)
        self.configuracao.pack(side="left")

        #Inicialização da Lista de Presença
        self.lista = Lista(master = self, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0, presence_service= self.presence_service, on_select_participante= self.selecionar_aluno)
        self.lista.place(relx = 0.19, rely = 0.55, relwidth = 0.3, relheight = 0.7, anchor = "center")
        
        self.barra_nome_lista = CTkFrame(master = self, fg_color=("#EDF0F0", "#0E0D0D"), corner_radius=0)
        self.barra_nome_lista.place(relx = 0.19, rely = 0.175, relwidth = 0.3, relheight = 0.05, anchor = "center")

        self.nome_lista = CTkLabel(master = self.barra_nome_lista, text="Lista de presença")
        self.nome_lista.place(relx = 0.5, rely = 0.5, anchor = "center")

        #Inicialização do gabarito do aluno
        self.barra_nome_questoes = CTkFrame(master = self, fg_color=("#EDF0F0", "#0E0D0D"), corner_radius=0)
        self.barra_nome_questoes.place(relx = 0.5, rely = 0.175, relwidth = 0.3, relheight = 0.05, anchor = "center")

        self.nome_questoes = CTkLabel(master = self.barra_nome_questoes, text=f"Questões do aluno: Não selecionado")
        self.nome_questoes.place(relx = 0.5, rely = 0.5, anchor = "center")
        
        self.gabarito = Gabarito(master = self, question_service= self.question_service, selected= self.aluno_selecionado, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0)
        self.gabarito.place(relx = 0.5, rely = 0.535, relwidth = 0.3, relheight = 0.67, anchor = "center")

        self.barra_gabarito = CTkFrame(master = self, corner_radius=0)
        self.barra_gabarito.place(relx = 0.5, rely = 0.885, relwidth = 0.3, relheight = 0.03, anchor = "center")

        self.aplicar_rank = CTkButton(master = self.barra_gabarito, width = 128, fg_color="#00B6CE", hover_color="#31B3FF", corner_radius=0, text = "Aplicar")
        self.aplicar_rank.pack(side = "left", fill = "both")

        self.marcar_todos = CTkButton(master = self.barra_gabarito, width = 128, fg_color="transparent", hover_color="#202020", corner_radius=0, text = "Marcar tudo", command = lambda: self.marcacao(1))
        self.marcar_todos.pack(side = "left", fill = "both")

        self.desmarcar_todos = CTkButton(master = self.barra_gabarito, width = 128, fg_color="transparent", hover_color="#202020", corner_radius=0, text = "Desmarcar tudo", command = lambda: self.marcacao(0))
        self.desmarcar_todos.pack(side = "left", fill = "both")

        #Inicialização do Ranking
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
                text=f"Questões de: {nome}"
            )
            self.gabarito.selected = self.aluno_selecionado
            self.question_service.add_respostas(self.aluno_selecionado["id"])
            self.gabarito.renderizar()
    
    def abrir_configs(self):
        if hasattr(self, "toplevel") and self.toplevel.winfo_exists():
            self.toplevel.focus()
            return
        self.toplevel = Configuracoes(master= self, presence_service = self.presence_service, question_service= self.question_service)
        self.toplevel.title("Configurações")
        self.toplevel.geometry("500x700")
        self.toplevel.lift()
        self.toplevel.attributes("-topmost", True)
        self.toplevel.after(100, lambda: self.toplevel.attributes("-topmost", False))

    def marcacao(self, mark):
        self.question_service.marcar_todos(self.aluno_selecionado["id"], mark)
        self.gabarito.renderizar()
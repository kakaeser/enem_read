from customtkinter import *
from tkinter import filedialog, Menu
from frontend.lista import Lista
from frontend.configuracoes import Configuracoes
from frontend.gabarito import Gabarito
from frontend.rank import Rank
from frontend.theme import COLORS
from backend.services.presence_service import PresenceService
from backend.services.question_service import QuestionService
from backend.services.ranking_service import RankingService

set_appearance_mode("Dark")

class App(CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1280x720")
        self.title("Enem da Read")
        self.config(bg=COLORS["bg"])
        self.aluno_selecionado = None
        self.presence_service = PresenceService()
        self.question_service = QuestionService()
        self.ranking_service = RankingService()
        
        
        #Inicilização do menu
        self.menu = CTkFrame(master = self, fg_color=COLORS["cards"], corner_radius=0)
        self.menu.place(relx = 0.5, rely = 0.02, relwidth = 1, relheight = 0.04, anchor = "center")

        self.arquivos = CTkButton(master = self.menu, fg_color= "transparent", hover_color= COLORS["hover"], text = "Arquivos", corner_radius= 0)
        self.arquivos.pack(side="left")
        self.arquivos.bind("<Button-1>", self.abrir_menu_arquivos)

        self.central_frame= CTkFrame(master = self, fg_color=COLORS["bg2"], corner_radius=32, bg_color= COLORS["bg"])
        self.central_frame.place(relx = 0.5, rely= 0.5, anchor= "center", relwidth = 0.95, relheight = 0.85)
        
        #Inicialização da Lista de Presença
        self.lista = Lista(master = self.central_frame, fg_color=COLORS["bg"], corner_radius=0, presence_service= self.presence_service, on_select_participante= self.selecionar_aluno)
        self.lista.place(relx = 0.19, rely = 0.5, relwidth = 0.3, relheight = 0.77, anchor = "center")
        
        self.barra_nome_lista = CTkFrame(master = self.central_frame, fg_color=COLORS["bg3"], corner_radius=0)
        self.barra_nome_lista.place(relx = 0.19, rely = 0.09, relwidth = 0.3, relheight = 0.05, anchor = "center")

        self.nome_lista = CTkLabel(master = self.barra_nome_lista, text="Lista de presença")
        self.nome_lista.place(relx = 0.5, rely = 0.5, anchor = "center")

        
        #Inicialização do gabarito do aluno
        
        self.gabarito = Gabarito(master = self.central_frame, question_service= self.question_service, selected= self.aluno_selecionado, fg_color=COLORS["bg"], corner_radius=0)
        self.gabarito.place(relx = 0.5, rely = 0.5, relwidth = 0.3, relheight = 0.77, anchor = "center")

        self.barra_nome_questoes = CTkFrame(master = self.central_frame, fg_color=COLORS["bg3"], corner_radius=0)
        self.barra_nome_questoes.place(relx = 0.5, rely = 0.09, relwidth = 0.3, relheight = 0.05, anchor = "center")

        self.nome_questoes = CTkLabel(master = self.barra_nome_questoes, text=f"Questões do aluno: Não selecionado")
        self.nome_questoes.place(relx = 0.5, rely = 0.5, anchor = "center")

        self.barra_gabarito = CTkFrame(master = self.central_frame, corner_radius=0)
        self.barra_gabarito.place(relx = 0.5, rely = 0.885, relwidth = 0.3, relheight = 0.05, anchor = "center")

        self.aplicar_rank = CTkButton(master = self.barra_gabarito, width = 128, fg_color=COLORS["primary"], hover_color=COLORS["hover"], corner_radius=0, text = "Aplicar", command = lambda: self.rank.renderizar())
        self.aplicar_rank.pack(side = "left", fill = "both")

        self.marcar_todos = CTkButton(master = self.barra_gabarito, width = 128, fg_color=COLORS["cards"], hover_color=COLORS["hover"], corner_radius=0, text = "Marcar tudo", command = lambda: self.marcacao(1))
        self.marcar_todos.pack(side = "left", fill = "both")

        self.desmarcar_todos = CTkButton(master = self.barra_gabarito, width = 128, fg_color=COLORS["cards"], hover_color=COLORS["hover"], corner_radius=0, text = "Desmarcar tudo", command = lambda: self.marcacao(0))
        self.desmarcar_todos.pack(side = "left", fill = "both")

        #Inicialização do Ranking 
        self.rank = Rank(master = self.central_frame, fg_color=COLORS["bg"], corner_radius=0)
        self.rank.place(relx = 0.81, rely = 0.5, relwidth = 0.3, relheight = 0.77, anchor = "center")

        self.barra_nome_rank = CTkFrame(master = self.central_frame, fg_color=COLORS["bg3"], corner_radius=0)
        self.barra_nome_rank.place(relx = 0.81, rely = 0.09, relwidth = 0.3, relheight = 0.05, anchor = "center")

        self.nome_rank = CTkLabel(master = self.barra_nome_rank, text="Ranking")
        self.nome_rank.place(relx = 0.5, rely = 0.5, anchor = "center")

        self.barra_rank = CTkFrame(master = self.central_frame, corner_radius=0)
        self.barra_rank.place(relx = 0.81, rely = 0.885, relwidth = 0.3, relheight = 0.05, anchor = "center")

        self.copiar_rank = CTkButton(master = self.barra_rank, width = 192, fg_color=COLORS["cards"], hover_color=COLORS["hover"], corner_radius=0, text = "Copiar Rank", command = lambda: self.copiar_rank())
        self.copiar_rank.pack(side = "left", fill = "both")

        self.export_rank = CTkButton(master = self.barra_rank, width = 192, fg_color=COLORS["cards"], hover_color=COLORS["hover"], corner_radius=0, text = "Exportar Rank", command = lambda: self.exportar())
        self.export_rank.pack(side = "left", fill = "both")

        self.label_rank = CTkLabel(master= self.central_frame, text= "")
        self.label_rank.place(relx= 0.81, rely= 0.93, anchor= "center")
        
        
        self.credits = CTkLabel(master= self, text= "Made by kakaeser", fg_color=COLORS["bg"], text_color= COLORS["text"])
        self.credits.place(relx= 0.09, rely= 0.95, anchor= "center")
        
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
        self.toplevel = Configuracoes(master= self, presence_service = self.presence_service, question_service= self.question_service, ranking_service= self.ranking_service, on_update= self.atualizar_telas)
        self.toplevel.title("Configurações")
        self.toplevel.geometry("500x500")
        self.toplevel.lift()
        self.toplevel.attributes("-topmost", True)
        self.toplevel.after(100, lambda: self.toplevel.attributes("-topmost", False))

    def marcacao(self, mark):
        self.question_service.marcar_todos(self.aluno_selecionado["id"], mark)
        self.gabarito.renderizar()
    
    def atualizar_telas(self):
        self.lista.renderizar()
        self.gabarito.renderizar()
        self.rank.renderizar()
    
    def copiar_rank(self):
        texto = ""
        
        for i, r in enumerate(self.rank.ranking, start=1):
            if r["nota"] == "-":
                nota = 0
            else:
                nota = float(r["nota"])
            texto += f"{i}º - {r['nome']} - {nota:.2f}\n"


        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update()
        self.label_rank.configure(text = "Rank copiado!!!")

    
    def importar_lista(self):
        caminho = filedialog.askopenfilename(
            title="Selecionar arquivo Excel",
            filetypes=[("Excel", "*.xlsx *.xls")],
            parent=self
        )

        if not caminho:
            print("Problema no caminho")
            return  

    def abrir_menu_arquivos(self, event):
        menu = Menu(self, tearoff=0, bg=COLORS["cards"], fg=COLORS["text"],activebackground=COLORS["hover"])

        menu.add_command(label="Importar gabarito")
        menu.add_separator()
        menu.add_command(label="Importar lista de chamada", command= self.abrir_configs)

        # posição logo abaixo do botão
        x = event.widget.winfo_rootx()
        y = event.widget.winfo_rooty() + event.widget.winfo_height()

        menu.post(x, y)
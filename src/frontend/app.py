from customtkinter import *

set_appearance_mode("Dark")

class App(CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1280x720")
        self.title("Enem da Read")
        self.aluno_selecionado = None

    def abrir_app(self):
        
        barrahori = CTkFrame(master = app, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0)
        barrahori.place(relx = 0.5, rely = 0, relwidth = 1, relheight = 0.05, anchor = "center")

        barra_nome_lista = CTkFrame(master = app, fg_color=("#EDF0F0", "#0E0D0D"), corner_radius=0)
        barra_nome_lista.place(relx = 0.19, rely = 0.175, relwidth = 0.3, relheight = 0.05, anchor = "center")

        nome_lista = CTkLabel(master = barra_nome_lista, text="Lista de presença")
        nome_lista.place(relx = 0.5, rely = 0.5, anchor = "center")
        
        lista = CTkScrollableFrame(master = app, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0)
        lista.place(relx = 0.19, rely = 0.55, relwidth = 0.3, relheight = 0.7, anchor = "center")


        barra_nome_questoes = CTkFrame(master = app, fg_color=("#EDF0F0", "#0E0D0D"), corner_radius=0)
        barra_nome_questoes.place(relx = 0.5, rely = 0.175, relwidth = 0.3, relheight = 0.05, anchor = "center")

        

        nome_questoes = CTkLabel(master = barra_nome_questoes, text=f"Questões do aluno {self.aluno_selecionado}")
        nome_questoes.place(relx = 0.5, rely = 0.5, anchor = "center")
        
        questoes = CTkScrollableFrame(master = app, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0)
        questoes.place(relx = 0.5, rely = 0.55, relwidth = 0.3, relheight = 0.7, anchor = "center")


        barra_nome_rank = CTkFrame(master = app, fg_color=("#EDF0F0", "#0E0D0D"), corner_radius=0)
        barra_nome_rank.place(relx = 0.81, rely = 0.175, relwidth = 0.3, relheight = 0.05, anchor = "center")

        nome_rank = CTkLabel(master = barra_nome_rank, text="Ranking")
        nome_rank.place(relx = 0.5, rely = 0.5, anchor = "center")
        
        rank = CTkScrollableFrame(master = app, fg_color=("#DDE7E7", "#1B1B1B"), corner_radius=0)
        rank.place(relx = 0.81, rely = 0.55, relwidth = 0.3, relheight = 0.7, anchor = "center")

        app.mainloop()

app = App()
app.abrir_app()
from customtkinter import *
from backend.services.ranking_service import RankingService

class Rank(CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.service = RankingService()
        self.ranking = []

        self.renderizar()

    def renderizar(self):
        for widget in self.winfo_children():
            widget.destroy()

        if not self.ranking:
            CTkLabel(
                self,
                text="Nenhuma nota foi computada"
            ).pack(pady=20)
        self.ranking = self.service.gerar_ranking()
        i = 0
        for p in self.ranking:
            i +=1
            self.criar_linha(p, i)
    
    def criar_linha(self, rank, num):
        nota_valor = rank.get("nota")
        if nota_valor != "-":
            nota_texto = f"{float(nota_valor):.2f}"
        else:
            nota_texto = nota_valor

        linha = CTkFrame(master = self)
        linha.pack(fill="x", padx=2, pady=2)

        posicao = CTkLabel(linha,text=f"#{num}",fg_color="transparent", anchor= "w", width = 20)

        sep1 = CTkFrame(linha, width=4, fg_color="#111111", height=30)

        nome = CTkLabel(linha,text=f"{rank['nome']}",fg_color="transparent", anchor= "w")

        sep2 = CTkFrame(linha, width=4, fg_color="#111111", height=30)

        nota = CTkLabel(linha,text=f"{nota_texto}",fg_color="transparent", anchor= "e", width = 45)
        
        
        posicao.pack(side="left", padx= 5)
        sep1.pack(side="left", padx= 5)
        nome.pack(side="left", padx= 5)
        nota.pack(side="right", padx= 20)
        sep2.pack(side="right", padx= 5)

        if num == 1:
            linha.configure(fg_color= "#A08300")
            sep1.configure(fg_color= "#665300")
            sep2.configure(fg_color= "#665300")
        if num == 2:
            linha.configure(fg_color= "#4F8E91")
            sep1.configure(fg_color= "#3E7072")
            sep2.configure(fg_color= "#3E7072")
        if num == 3:
            linha.configure(fg_color= "#9E5A00")
            sep1.configure(fg_color= "#794400")
            sep2.configure(fg_color= "#794400")
        if num >= 4 and num <= 5:
            linha.configure(fg_color= "#5171FD")
            sep1.configure(fg_color= "#213BB1")
            sep2.configure(fg_color= "#213BB1")
        
from customtkinter import *
from frontend.theme import COLORS

class Gabarito(CTkScrollableFrame):
    def __init__(self, master, question_service,selected, **kwargs):
        super().__init__(master, **kwargs)

        self.service = question_service
        self.selected = selected

        self.renderizar()

    def renderizar(self):
        for widget in self.winfo_children():
            widget.destroy()

        if not self.selected:
            CTkLabel(
                self,
                text="Nenhum aluno selecionado"
            ).pack(pady=20)
            return
        questoes = self.service.listar_questoes(self.selected["id"])
        if not questoes:
            CTkLabel(
                self,
                text="Nenhuma questão criada"
            ).pack(pady=20)
            return
        else:
            for p in questoes:
                self.criar_linha(p)
    
    def criar_linha(self, questao):
        linha = CTkFrame(master = self, fg_color=COLORS["cards"])
        linha.pack(fill="x", padx=2, pady=2)

        numero_questao = CTkLabel(
            linha,
            text=f"Q{questao['numero']}:",
            fg_color="transparent"
        )

        var = IntVar(value= int(questao["acerto"]))
        checkbox = CTkCheckBox(
            linha,
            text="",
            variable=var,
            fg_color=COLORS["primary2"],
            hover_color=COLORS["primary2"],
            corner_radius= 0,
            command=lambda pid=self.selected["id"], qid= questao["id"], v=var:
                self.service.marcar_acertos(pid,qid,v.get())
        
        )
        
        numero_questao.pack(side="left", expand=True, padx=(8, 4))
        checkbox.pack(side="right", padx=(4, 8))
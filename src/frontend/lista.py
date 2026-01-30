from customtkinter import *

class Lista(CTkScrollableFrame):
    def __init__(self, master, presence_service, on_select_participante, **kwargs):
        super().__init__(master, **kwargs)

        self.service = presence_service
        self.on_select_participante = on_select_participante

        self.renderizar()

    def renderizar(self):
        for widget in self.winfo_children():
            widget.destroy()
            
        participantes = self.service.listar_nomes()
        if not participantes:
            CTkLabel(
                self,
                text="Nenhum participante cadastrado"
            ).pack(pady=20)
            return
        else:
            for p in participantes:
                self.criar_linha(p)
    
    def criar_linha(self, participante):
        linha = CTkFrame(master = self)
        linha.pack(fill="x", padx=2, pady=2)

        var = IntVar(value= int(participante["presente"]))
        checkbox = CTkCheckBox(
            linha,
            text="",
            variable=var,
            width = 20,
            fg_color="#31B3FF",
            hover_color="#31B3FF",
            corner_radius= 0,
            command=lambda pid=participante["id"], v=var:
                self.service.marcar_presenca(pid, v.get())
        )
        
        botao_nome = CTkButton(
            linha,
            text=participante["nome"],
            fg_color="transparent",
            hover_color=("#EDF0F0", "#353535"),
            corner_radius= 0 ,
            anchor="w",
            command=lambda:
                self.on_select_participante(
                    participante["id"],
                    participante["nome"]
                )
        )
        botao_nome.pack(side="left", fill="x", expand=True, padx=(8, 4))
        checkbox.pack(side="right", padx=(4, 8))

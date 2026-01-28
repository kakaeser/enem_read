from customtkinter import *

class Lista(CTkScrollableFrame):
    def __init__(self, master, presence_service, on_select_participante, **kwargs):
        super().__init__(master, **kwargs)

        self.service = presence_service
        self.on_select_participante = on_select_participante

        self.renderizar()

    def renderizar(self):
        participantes = self.service.listar_nomes()
        if not participantes:
            CTkLabel(
                self.lista,
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
            command=lambda pid=participante["id"], v=var:
                self.service.marcar_presenca(pid, v.get())
        )
        checkbox.pack(side="left")
        botao_nome = CTkButton(
            linha,
            text=participante["nome"],
            fg_color="transparent",
            hover_color=("#EDF0F0", "#353535"),
            anchor="w",
            command=lambda:
                self.on_select_participante(
                    participante["id"],
                    participante["nome"]
                )
        )
        botao_nome.pack(side="left", fill="x", expand=True, padx=2)

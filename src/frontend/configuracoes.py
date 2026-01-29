from customtkinter import *
from backend.seed.seed1 import seed_participantes_json

class Configuracoes(CTkToplevel):
    def __init__(self, master, presence_service,question_service,ranking_service,on_update, **kwargs):
        super().__init__(master, **kwargs)

        self.p_service = presence_service
        self.q_service = question_service
        self.r_service = ranking_service
        self.on_update = on_update

        self.frame = CTkFrame(master= self, fg_color="transparent")
        self.frame.pack(fill="both")

        self.label_questoes = CTkLabel(master = self.frame, text = "Configurações das Questões", font= ("Montserrat", 20))
        self.label_questoes.pack(pady = 8, padx= 16, anchor="w")

        self.numero_questao = CTkEntry(master = self.frame, placeholder_text="Numero de questões Ex: 60", width= 400, fg_color="transparent")
        self.numero_questao.pack(pady = 8, padx= 16, anchor ="w")

        self.questao_peso = CTkEntry(master = self.frame, placeholder_text="Numero das questões com peso Ex: 10, 12, 17", width= 400, fg_color="transparent")
        self.questao_peso.pack(pady = 8, padx= 16, anchor ="w")

        self.nota_simbolica = CTkEntry(master = self.frame, placeholder_text="Nota maxima simbólica Ex: 1000", width= 400, fg_color="transparent")
        self.nota_simbolica.pack(pady = 8, padx= 16, anchor ="w")

        self.confirm = CTkButton(master = self.frame, corner_radius= 0, text = "Aplicar", hover_color= "#1B1B1B", fg_color= "#3a3a3a", command = lambda: self.confirmar_questoes(self.numero_questao.get(), self.questao_peso.get(), self.nota_simbolica.get()))
        self.confirm.pack(pady = 8, padx= 16, anchor ="w")

        self.erro_label = CTkLabel(master = self.frame, text = "", font= ("Montserrat", 12), text_color="#FF0000")
        self.erro_label.pack(pady = 8, padx= 16, anchor ="w")

        self.label_questoes = CTkLabel(master = self.frame, text = "Configurações de importação", font= ("Montserrat", 20))
        self.label_questoes.pack(pady = 8, padx= 16, anchor="w")

        self.import_fake = CTkButton(master = self.frame, corner_radius= 0, text = "Importar Dados Fake", hover_color= "#1B1B1B", fg_color= "#3a3a3a", command = lambda: self.import_dados_fake)
        self.import_fake.pack(pady = 8, padx= 16, anchor ="w", side = "left")

        self.import_real = CTkButton(master = self.frame, corner_radius= 0, text = "Importar Dados", hover_color= "#1B1B1B", fg_color= "#3a3a3a")
        self.import_real.pack(pady = 8, padx= 16, anchor ="w", side = "left")

    def confirmar_questoes(self, n_questoes, pesos, nota_simb):
        if n_questoes == None or pesos == None:
            self.erro_label.configure(text="Dados não inseridos",text_color="#FF0000")
            return
        
        try:
            n_questoes = int(n_questoes)
        except ValueError:
            self.erro_label.configure(text="Número de questões inválido",text_color="#FF0000")
            return
        
        try:
            nota_simb = int(nota_simb)
        except ValueError:
            nota_simb = 1000
    
        if n_questoes <= 0:
            self.erro_label.configure(text="Numero de questões inválido",text_color="#FF0000")
            return
        
        n_pesos = self.q_service.string_para_numeros(pesos)
        n_pesos = list(set(n_pesos))
        for p in n_pesos:
            if p > n_questoes or p < 1:
                self.erro_label.configure(text="Alguma das questões selecionadas para peso 2 não existe",text_color="#FF0000")
                return
            
        self.q_service.delete_all()
        self.q_service.criar_questoes(n_questoes, n_pesos)
        nota_max = self.q_service.calcular_nota_maxima()
        self.r_service.config_mani(nota_max, nota_simb)
        self.erro_label.configure(text="Questões Adicionadas com sucesso",text_color="#C4C4C4")

    def import_dados_fake(self):
        seed_participantes_json()
        self.on_update()

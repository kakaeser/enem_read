# Supported languages
LANGUAGES = ["pt_BR", "en"]

# Translation dictionaries
STRINGS: dict[str, dict[str, str]] = {
    "pt_BR": {
        "app_title": "Enem da Read",
        "create_exam": "Criar Prova",
        "open_exam": "Abrir Prova",
        "exam_name": "Nome da Prova",
        "questions_count": "Número de Questões",
        "symbolic_note": "Nota Máxima",
        "create_and_open": "Criar e Abrir",
        "no_exams": "Nenhuma prova encontrada. Crie uma acima.",
        "dashboard": "Ranking",
        "presence": "Presença",
        "share": "Compartilhar",
        "copy_link": "Copiar Link",
        "import_participants": "Importar Participantes",
        "save": "Salvar",
        "close": "Fechar",
        "refresh": "Atualizar",
        "rank": "Pos.",
        "name": "Nome",
        "score": "Nota",
        "accuracy": "Acertos %",
        "essay_points": "Pontos Redação",
        "correct_answer": "Gabarito",
        "marked_answer": "Resposta",
        "result": "Resultado",
        "weight": "Peso",
        "present": "Presente",
        "language": "Idioma",
        "settings": "Configurações",
        "select_language": "Selecione o idioma",
        "error_required": "Campo obrigatório",
        "error_positive_int": "Deve ser um número inteiro positivo",
        "error_essay_points": "Pontos de redação devem ser ≥ 0",
        "saved": "Salvo",
        "upload_answer_sheet": "Enviar Gabarito",
        "select_exam": "Selecione a Prova",
        "select_participant": "Selecione o Participante",
        "select_image": "Selecionar Imagem",
        "submit": "Enviar",
        "mobile_server_warning": "Servidor móvel rodando apenas em localhost — compartilhamento via rede indisponível",
        "api_start_error": "Não foi possível iniciar o servidor. Inicie manualmente.",
        "connecting": "Conectando...",
        "end_exam": "Encerrar Prova",
        "end_exam_confirm": "Encerrar Prova? Esta ação não pode ser desfeita.",
        "end_exam_warning": "Após encerrar, nenhuma edição será permitida.",
        "cancel": "Cancelar",
        "exam_ended_at": "Encerrada em",
        "exam_completed": "Concluída",
        "view_only": "Somente Visualização",
    },
    "en": {
        "app_title": "Enem da Read",
        "create_exam": "Create Exam",
        "open_exam": "Open Exam",
        "exam_name": "Exam Name",
        "questions_count": "Number of Questions",
        "symbolic_note": "Max Score",
        "create_and_open": "Create & Open",
        "no_exams": "No exams yet. Create one above.",
        "dashboard": "Rankings",
        "presence": "Attendance",
        "share": "Share",
        "copy_link": "Copy Link",
        "import_participants": "Import Participants",
        "save": "Save",
        "close": "Close",
        "refresh": "Refresh",
        "rank": "Rank",
        "name": "Name",
        "score": "Score",
        "accuracy": "Accuracy %",
        "essay_points": "Essay Points",
        "correct_answer": "Answer Key",
        "marked_answer": "Response",
        "result": "Result",
        "weight": "Weight",
        "present": "Present",
        "language": "Language",
        "settings": "Settings",
        "select_language": "Select language",
        "error_required": "Required field",
        "error_positive_int": "Must be a positive integer",
        "error_essay_points": "Essay points must be ≥ 0",
        "saved": "Saved",
        "upload_answer_sheet": "Upload Answer Sheet",
        "select_exam": "Select Exam",
        "select_participant": "Select Participant",
        "select_image": "Select Image",
        "submit": "Submit",
        "mobile_server_warning": "Mobile server running on localhost only — LAN sharing unavailable",
        "api_start_error": "Could not start API server. Please start it manually.",
        "connecting": "Connecting...",
        "end_exam": "End Exam",
        "end_exam_confirm": "End Exam? This action cannot be undone.",
        "end_exam_warning": "After ending, no edits will be allowed.",
        "cancel": "Cancel",
        "exam_ended_at": "Ended at",
        "exam_completed": "Completed",
        "view_only": "View Only",
    },
}

_active_lang: str = "pt_BR"


def set_language(lang: str) -> None:
    global _active_lang
    if lang not in LANGUAGES:
        raise ValueError(f"Unsupported language: {lang}")
    _active_lang = lang


def get_language() -> str:
    return _active_lang


def t(key: str) -> str:
    return STRINGS.get(_active_lang, {}).get(key, key)

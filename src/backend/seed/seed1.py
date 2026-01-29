import json
import os

from backend.config.connection import DBConnectionHandler
from backend.entities.participante import Participante


def seed_participantes_json():
    # caminho do json
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(BASE_DIR, "participantes.json")

    with open(json_path, "r", encoding="utf-8") as file:
        dados = json.load(file)

    participantes = [
        Participante(
            nome=p["nome"],
            email=p["email"],
            cpf=p["cpf"]
        )
        for p in dados
    ]

    with DBConnectionHandler() as db:
        db.session.add_all(participantes)

    print("✅ Participantes inseridos a partir do JSON com sucesso!")


if __name__ == "__main__":
    seed_participantes_json()


#Código para rodar
"""
cd src
python -m backend.seed.seed1
cd ..\

"""
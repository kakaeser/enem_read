from backend.entities.config import Config
from backend.config.connection import DBConnectionHandler


class ConfigRepo:
    def add(self, nota_max, nota_simb):
        data = Config(nota_max = nota_max, nota_simb = nota_simb)
        with DBConnectionHandler() as db:
            db.session.add(data)
        return True
    
    def conferir(self):
        with DBConnectionHandler() as db:
            data = db.session.query(Config).filter(Config.id == 1).first()
            if data:
                return True
            elif not data:
                return False
    
    def alterar(self,nota_max, nota_simb):
        with DBConnectionHandler() as db:
            data = (db.session.query(Config).filter(Config.id == 1).first())
            if not data:
                return False
            
            data.nota_max = nota_max
            data.nota_simb = nota_simb
            return True
    
    def get_notas(self):
        with DBConnectionHandler() as db:
            data = db.session.query(Config).filter(Config.id == 1).first()
            if not data:
                return None
            
            return {"nota_max": data.nota_max, "nota_simb": data.nota_simb} 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

class DBConnectionHandler:
    def __init__(self) -> None:

        DIR_ATUAL = os.path.dirname(os.path.abspath(__file__)) 
        DIR_PAI = os.path.dirname(DIR_ATUAL)                   
        DB_PATH = os.path.join(DIR_PAI, "database.db")

        self.__connection_string = f"sqlite:///{DB_PATH}"    
        self.__engine = self.__create_database_engine()
        self.session = None

    def __create_database_engine(self):
        engine = create_engine(self.__connection_string)
        return engine

    def get_engine(self):
        return self.__engine
    
    def __enter__(self):
        sessionmake = sessionmaker(bind=self.__engine)
        self.session = sessionmake()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import backend.entities  


class DBConnectionHandler:
    _engine = None  

    def __init__(self) -> None:
        if DBConnectionHandler._engine is None:
            DBConnectionHandler._engine = self._create_engine()

        self.session = None

    @staticmethod
    def _create_engine():
        base_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.getcwd()),
            "enem_read"
        )

        os.makedirs(base_dir, exist_ok=True)

        db_path = os.path.join(base_dir, "database.db")

        connection_string = f"sqlite:///{db_path}"

        return create_engine(
            connection_string,
            echo=False,
            future=True
        )

    def get_engine(self):
        return DBConnectionHandler._engine

    def __enter__(self):
        Session = sessionmaker(
            bind=self.get_engine(),
            autoflush=False,
            autocommit=False
        )
        self.session = Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
        finally:
            self.session.close()

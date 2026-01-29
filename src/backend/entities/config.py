from sqlalchemy import Column, Integer
from backend.config.base import Base

class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key= True)
    nota_max = Column(Integer)
    nota_simb = Column(Integer, default = 1000)

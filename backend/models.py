from sqlalchemy import Column, Integer, String, UniqueConstraint
from database import Base

class Creator(Base):
    __tablename__ = "users_creators"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class Business(Base):
    __tablename__ = "users_businesses"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    business_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)

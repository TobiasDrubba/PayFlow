from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
import os

from app.domain.models import User

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class UserORM(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

def create_user_table():
    Base.metadata.create_all(bind=engine)

def get_user_by_username(db, username: str):
    return db.query(UserORM).filter(UserORM.username == username).first()

def create_user(db, username: str, hashed_password: str, email: str = None):
    db_user = UserORM(username=username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db, user_id: int):
    return db.query(UserORM).filter(UserORM.id == user_id).first()


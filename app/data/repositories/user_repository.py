from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker

from app.data.base import Base, engine

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


def create_user(db, username: str, hashed_password: str):
    db_user = UserORM(username=username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user(db, user_id: int):
    return db.query(UserORM).filter(UserORM.id == user_id).first()


def delete_user(db, user_id: int):
    user = db.query(UserORM).filter(UserORM.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False

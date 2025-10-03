from app.data.base import Base
from app.data.repositories.payment_repository import engine

Base.metadata.create_all(bind=engine)

from app.data.user_repository import UserORM
from app.data.payment_repository import PaymentORM, CategoryTreeORM
from app.data.base import Base
from app.data.payment_repository import engine

Base.metadata.create_all(bind=engine)

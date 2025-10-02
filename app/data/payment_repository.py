# app/data/repository.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SAEnum, Text, ForeignKey
from sqlalchemy.orm import sessionmaker

import json
from typing import List
from app.data.base import Base
from app.data.base import engine

from app.domain.models import Payment, PaymentSource, PaymentType

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class PaymentORM(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    merchant = Column(String, nullable=False)
    auto_category = Column(String, default="Uncategorized")
    source = Column(SAEnum(PaymentSource), nullable=False)
    type = Column(SAEnum(PaymentType), nullable=False)
    note = Column(String, default="")
    category = Column(String, default="")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

class CategoryTreeORM(Base):
    __tablename__ = "category_trees"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    tree_json = Column(Text, nullable=False)

def create_payment_tables():
    Base.metadata.create_all(bind=engine)

def payment_to_domain(payment_orm: PaymentORM) -> Payment:
    return Payment(
        id=payment_orm.id,
        date=payment_orm.date,
        amount=payment_orm.amount,
        currency=payment_orm.currency,
        merchant=payment_orm.merchant,
        auto_category=payment_orm.auto_category,
        source=payment_orm.source,
        type=payment_orm.type,
        note=payment_orm.note,
        category=payment_orm.category,
        user_id=payment_orm.user_id,
    )

def get_all_payments(db, user_id: int) -> List[Payment]:
    payments = db.query(PaymentORM).filter(PaymentORM.user_id == user_id).all()
    return [payment_to_domain(p) for p in payments]

def upsert_payments(db, payments: List[Payment], user_id: int) -> int:
    count = 0
    for p in payments:
        exists = db.query(PaymentORM).filter_by(id=p.id, user_id=user_id).first()
        if not exists:
            db.add(PaymentORM(
                id=p.id,
                date=p.date,
                amount=p.amount,
                currency=p.currency,
                merchant=p.merchant,
                auto_category=p.auto_category,
                source=p.source,
                type=p.type,
                note=p.note,
                category=p.category,
                user_id=user_id,
            ))
            count += 1
    db.commit()
    return count

def save_payments(db, payments: List[Payment], user_id: int):
    # Overwrite all payments for user
    db.query(PaymentORM).filter(PaymentORM.user_id == user_id).delete()
    for p in payments:
        db.add(PaymentORM(
            id=p.id,
            date=p.date,
            amount=p.amount,
            currency=p.currency,
            merchant=p.merchant,
            auto_category=p.auto_category,
            source=p.source,
            type=p.type,
            note=p.note,
            category=p.category,
            user_id=user_id,
        ))
    db.commit()

def get_category_tree(db, user_id: int) -> dict:
    tree = db.query(CategoryTreeORM).filter(CategoryTreeORM.user_id == user_id).first()
    if tree:
        return json.loads(tree.tree_json)
    return {}

def save_category_tree(db, user_id: int, tree: dict):
    tree_json = json.dumps(tree, ensure_ascii=False)
    obj = db.query(CategoryTreeORM).filter(CategoryTreeORM.user_id == user_id).first()
    if obj:
        obj.tree_json = tree_json
    else:
        obj = CategoryTreeORM(user_id=user_id, tree_json=tree_json)
        db.add(obj)
    db.commit()

def get_all_child_categories(tree: dict) -> list:
    result = set()
    def collect(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if v is None:
                    result.add(k)
                else:
                    collect(v)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, str):
                    result.add(item)
                else:
                    collect(item)
    collect(tree)
    return sorted(result)

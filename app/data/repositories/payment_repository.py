# app/data/repository.py
import json
from typing import List

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import sessionmaker

from app.data.base import Base, engine
from app.domain.models.payment import Payment, PaymentSource, PaymentType

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class PaymentORM(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
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
        exists = (
            db.query(PaymentORM)
            .filter_by(
                date=p.date, amount=p.amount, merchant=p.merchant, user_id=user_id
            )
            .first()
        )
        if not exists:
            db.add(
                PaymentORM(
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
                )
            )
            count += 1
    db.commit()
    return count


def add_payment(db, payment: Payment, user_id: int) -> Payment:
    exists = (
        db.query(PaymentORM)
        .filter_by(
            date=payment.date,
            amount=payment.amount,
            merchant=payment.merchant,
            user_id=user_id,
        )
        .first()
    )
    if exists:
        raise ValueError(
            "Duplicate payment (same date, amount, merchant) already exists"
        )
    payment_orm = PaymentORM(
        date=payment.date,
        amount=payment.amount,
        currency=payment.currency,
        merchant=payment.merchant,
        auto_category=payment.auto_category,
        source=payment.source,
        type=payment.type,
        note=payment.note,
        category=payment.category,
        user_id=user_id,
    )
    db.add(payment_orm)
    db.commit()
    db.refresh(payment_orm)
    return payment_to_domain(payment_orm)


def update_payment_category(
    db, payment_id: int, user_id: int, cust_category: str
) -> bool:
    payment = db.query(PaymentORM).filter_by(id=payment_id, user_id=user_id).first()
    if not payment:
        return False
    payment.category = cust_category
    db.commit()
    return True


def update_merchant_categories(
    db, payment_id: int, user_id: int, cust_category: str
) -> int:
    payment = db.query(PaymentORM).filter_by(id=payment_id, user_id=user_id).first()
    if not payment:
        return 0
    merchant = payment.merchant
    updated = (
        db.query(PaymentORM)
        .filter_by(merchant=merchant, user_id=user_id)
        .update({"category": cust_category})
    )
    db.commit()
    return updated


def delete_payments_by_ids(db, ids: list, user_id: int) -> int:
    deleted = (
        db.query(PaymentORM)
        .filter(PaymentORM.id.in_(ids), PaymentORM.user_id == user_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


def get_category_tree(db, user_id: int) -> dict:
    tree = db.query(CategoryTreeORM).filter(CategoryTreeORM.user_id == user_id).first()
    if tree:
        return json.loads(tree.tree_json)
    return {
        "Food": {
            "Restaurant": None,
            "Canteen": {
                "Canteen Breakfast": None,
                "Canteen Lunch": None,
                "Canteen Dinner": None,
                "Card Recharge": None,
            },
        }
    }


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

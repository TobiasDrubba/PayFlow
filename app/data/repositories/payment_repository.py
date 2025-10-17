# app/data/repository.py
import json
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import Column, Date, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text, cast, func, or_
from sqlalchemy.orm import sessionmaker

from app.data.base import Base, engine
from app.data.repositories.currency_repository import CurrencyRatesORM
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


def get_all_payments(
    db,
    user_id: int,
    currency: str | None = None,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
) -> tuple[list[Payment], int]:
    query = db.query(PaymentORM).filter(PaymentORM.user_id == user_id)
    if search:
        term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                PaymentORM.merchant.ilike(term),
                PaymentORM.auto_category.ilike(term),
                PaymentORM.category.ilike(term),
                PaymentORM.note.ilike(term),
                PaymentORM.currency.ilike(term),
                cast(PaymentORM.type, Text).ilike(term),
                cast(PaymentORM.source, Text).ilike(term),
            )
        )
    total = query.count()
    query = query.order_by(PaymentORM.date.desc())
    if currency in ("EUR", "USD"):
        query = query.join(
            CurrencyRatesORM, PaymentORM.date.cast(Date) == CurrencyRatesORM.date
        )
        if currency == "EUR":
            payments = (
                query.with_entities(
                    PaymentORM.id,
                    PaymentORM.date,
                    (PaymentORM.amount * CurrencyRatesORM.EURO).label("amount"),
                    PaymentORM.currency,
                    PaymentORM.merchant,
                    PaymentORM.auto_category,
                    PaymentORM.source,
                    PaymentORM.type,
                    PaymentORM.note,
                    PaymentORM.category,
                    PaymentORM.user_id,
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
        else:
            payments = (
                query.with_entities(
                    PaymentORM.id,
                    PaymentORM.date,
                    (PaymentORM.amount * CurrencyRatesORM.USD).label("amount"),
                    PaymentORM.currency,
                    PaymentORM.merchant,
                    PaymentORM.auto_category,
                    PaymentORM.source,
                    PaymentORM.type,
                    PaymentORM.note,
                    PaymentORM.category,
                    PaymentORM.user_id,
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
        return [
            Payment(
                id=p[0],
                date=p[1],
                amount=p[2],
                currency=currency,
                merchant=p[4],
                auto_category=p[5],
                source=p[6],
                type=p[7],
                note=p[8],
                category=p[9],
                user_id=p[10],
            )
            for p in payments
        ], total
    else:
        payments = query.offset((page - 1) * page_size).limit(page_size).all()
        return [payment_to_domain(p) for p in payments], total


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


def delete_all_user_data(db, user_id: int):
    db.query(PaymentORM).filter(PaymentORM.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(CategoryTreeORM).filter(CategoryTreeORM.user_id == user_id).delete(
        synchronize_session=False
    )
    db.commit()


def build_base_payment_filters(
    user_id: int,
    start_date=None,
    end_date=None,
    days: int | None = None,
):
    """
    Build SQLAlchemy filter list for payments, supporting days, start_date, end_date.
    """
    from app.domain.models.payment import PaymentType

    filters = [PaymentORM.user_id == user_id, PaymentORM.type != PaymentType.ABORT]
    if days is not None and days > 0:
        newest_payment = (
            SessionLocal()
            .query(func.max(PaymentORM.date))
            .filter(PaymentORM.user_id == user_id)
            .scalar()
        )
        if newest_payment:
            start_date_calc = (
                newest_payment.date()
                if hasattr(newest_payment, "date")
                else newest_payment
            )
            start_date_calc = start_date_calc - timedelta(days=days - 1)
            filters.append(PaymentORM.date >= start_date_calc)
            filters.append(PaymentORM.date <= newest_payment)
    else:
        if start_date:
            filters.append(PaymentORM.date >= start_date)
        if end_date:
            filters.append(PaymentORM.date <= end_date)
    return filters


def sum_payments_in_db_range(
    db,
    user_id: int,
    start: datetime | None,
    end: datetime | None,
    currency: str | None = None,
    days: int | None = None,
) -> float:
    filters = build_base_payment_filters(user_id, start, end, days)
    if currency in ("EUR", "USD"):
        if currency == "EUR":
            amount_expr = PaymentORM.amount * CurrencyRatesORM.EURO
        else:
            amount_expr = PaymentORM.amount * CurrencyRatesORM.USD
        total = (
            db.query(func.sum(amount_expr))
            .join(CurrencyRatesORM, PaymentORM.date.cast(Date) == CurrencyRatesORM.date)
            .filter(*filters)
            .scalar()
        )
        return total or 0.0
    else:
        total = db.query(func.sum(PaymentORM.amount)).filter(*filters).scalar()
        return total or 0.0


def all_merchant_same_category_db(
    db, user_id: int, merchant: str, cust_category: str
) -> bool:
    """
    Returns True if all payments for the given user and merchant have
    the given category, and there is more than one such payment.
    """

    # Count total payments for merchant
    total_count = (
        db.query(func.count(PaymentORM.id))
        .filter(PaymentORM.user_id == user_id, PaymentORM.merchant == merchant)
        .scalar()
    )
    if total_count <= 1:
        return False
    # Count payments for merchant with the given category
    category_count = (
        db.query(func.count(PaymentORM.id))
        .filter(
            PaymentORM.user_id == user_id,
            PaymentORM.merchant == merchant,
            PaymentORM.category == cust_category,
        )
        .scalar()
    )
    return total_count == category_count


def sum_payments_by_category_db(
    db,
    user_id: int,
    category_tree: dict,
    start_date=None,
    end_date=None,
    currency: str | None = None,
    days: int | None = None,
):
    """
    Aggregate payment amounts by category using the database layer.
    Returns: dict {category_name: sum, ...}, metadata
    """

    # Build all leaf categories and their paths
    def collect_paths(tree, path=None, paths=None):
        if tree is None:
            return paths if paths is not None else []
        if paths is None:
            paths = []
        if path is None:
            path = []
        for k, v in tree.items() if isinstance(tree, dict) else []:
            current_path = path + [k]
            if v is None:
                paths.append(current_path)
            elif isinstance(v, dict):
                if not v:
                    paths.append(current_path)
                else:
                    collect_paths(v, current_path, paths)
        return paths

    all_paths = collect_paths(category_tree)
    leaf_to_path = {p[-1]: p for p in all_paths}
    all_cats = set(cat for path in all_paths for cat in path)

    # Build base query
    filters = build_base_payment_filters(user_id, start_date, end_date, days)

    # Currency conversion
    if currency in ("EUR", "USD"):
        if currency == "EUR":
            amount_expr = PaymentORM.amount * CurrencyRatesORM.EURO
        else:
            amount_expr = PaymentORM.amount * CurrencyRatesORM.USD
        query = db.query(
            PaymentORM.category,
            func.sum(amount_expr).label("sum"),
        ).join(CurrencyRatesORM, PaymentORM.date.cast(Date) == CurrencyRatesORM.date)
    else:
        query = db.query(
            PaymentORM.category,
            func.sum(PaymentORM.amount).label("sum"),
        )

    query = query.filter(*filters).group_by(PaymentORM.category)
    rows = query.all()

    # Prepare result dict for all categories
    result = {cat: 0.0 for cat in all_cats}
    result["no category"] = 0.0
    result["invalid category"] = 0.0
    total_sum = 0.0
    invalid_categories_set = set()

    # Map DB results to aggregation
    for cat, s in rows:
        s = s or 0.0
        cat_key = cat.strip() if cat else None
        if not cat_key:
            result["no category"] += s
            total_sum += s
            continue
        path = leaf_to_path.get(cat_key)
        if not path:
            # Try partial match (for parent categories)
            for k, v in leaf_to_path.items():
                if cat_key == k or cat_key in v:
                    path = v
                    break
        if not path:
            result["invalid category"] += s
            invalid_categories_set.add(cat_key)
            total_sum += s
            continue
        for cat_in_path in path:
            result[cat_in_path] += s
        total_sum += s

    # Round all sums to zero decimal places
    for key in result:
        result[key] = round(result[key])

    output = {k: -v for k, v in result.items() if v != 0.0}
    metadata = {
        "total sum": round(total_sum),
        "invalid categories": sorted(list(invalid_categories_set)),
    }
    return output, metadata


def update_payments_category_bulk(
    db, user_id: int, categories: list, new_category: str
) -> int:
    """
    Bulk update payments for a user, set to new_category.
    Returns number of updated rows.
    """
    updated = (
        db.query(PaymentORM)
        .filter(PaymentORM.user_id == user_id, PaymentORM.category.in_(categories))
        .update({"category": new_category}, synchronize_session=False)
    )
    db.commit()
    return updated

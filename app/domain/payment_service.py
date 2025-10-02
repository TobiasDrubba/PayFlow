from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.domain.models import Payment, PaymentType
from app.data.payment_repository import (
    get_all_payments,
    save_payments,
    upsert_payments,
    get_category_tree,
    save_category_tree,
    get_all_child_categories,
    create_payment_tables,
)
from app.utils.aggregation import sum_payments_by_category, build_sankey_data
from app.utils.sum import sum_payments_in_range
from app.utils.alipay_parser import parse_alipay_file
import tempfile
import shutil
from app.domain.models import PaymentSource
import os
from fastapi.responses import StreamingResponse
import io
import csv
import json

create_payment_tables()

def child_categories(db: Session, user_id: int) -> List[str]:
    tree = get_category_tree(db, user_id)
    return get_all_child_categories(tree)

def _validate_category(db: Session, user_id: int, cust_category: str) -> None:
    valid_categories = set(child_categories(db, user_id))
    if cust_category not in valid_categories and cust_category != "":
        raise ValueError(f"Invalid child category: {cust_category}")

def update_category_tree(new_tree: Dict[str, Any], db: Session, user_id: int) -> None:
    old_tree = get_category_tree(db, user_id)
    old_child_categories = set(get_all_child_categories(old_tree))
    new_child_categories = set(get_all_child_categories(new_tree))
    deleted_categories = old_child_categories - new_child_categories
    payments = get_all_payments(db, user_id)
    changed = False
    for p in payments:
        if p.category in deleted_categories:
            p.category = ""
            changed = True
    if changed:
        save_payments(db, payments, user_id)
    save_category_tree(db, user_id, new_tree)

def update_payment_category(payment_id: str, cust_category: str, db: Session, user_id: int) -> None:
    _validate_category(db, user_id, cust_category)
    payments = get_all_payments(db, user_id)
    updated = False
    for p in payments:
        if p.id == payment_id:
            p.category = cust_category
            updated = True
            break
    if updated:
        save_payments(db, payments, user_id)
    else:
        raise ValueError(f"Payment with id {payment_id} not found")

def update_merchant_categories(payment_id: str, cust_category: str, db: Session, user_id: int) -> int:
    _validate_category(db, user_id, cust_category)
    payments = get_all_payments(db, user_id)
    merchant = None
    for p in payments:
        if p.id == payment_id:
            merchant = p.merchant
            break
    if merchant is None:
        raise ValueError(f"Payment with id {payment_id} not found")
    count = 0
    for p in payments:
        if p.merchant == merchant:
            p.category = cust_category
            count += 1
    if count > 0:
        save_payments(db, payments, user_id)
    return count

def import_alipay_payments(source_filepath: str, db: Session, user_id: int) -> int:
    payments = parse_alipay_file(source_filepath)
    for p in payments:
        p.user_id = user_id
    added = upsert_payments(db, payments, user_id)
    return added

def import_wechat_payments(source_filepath: str, db: Session, user_id: int) -> int:
    from app.utils.wechat_parser import parse_wechat_file
    payments = parse_wechat_file(source_filepath)
    for p in payments:
        p.user_id = user_id
    added = upsert_payments(db, payments, user_id)
    return added

def import_tsinghua_card_payments(source_filepath: str, db: Session, user_id: int) -> int:
    from app.utils.tsinghua_card_parser import parse_tsinghua_card_file
    payments = parse_tsinghua_card_file(source_filepath)
    for p in payments:
        p.user_id = user_id
    added = upsert_payments(db, payments, user_id)
    return added

def list_payments(db: Session, user_id: int) -> List[Payment]:
    return get_all_payments(db, user_id)

def get_payments_csv_stream(db: Session, user_id: int):
    payments = get_all_payments(db, user_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "date", "amount", "currency", "merchant",
        "auto_category", "source", "type", "note", "cust_category"
    ])
    for p in payments:
        writer.writerow([
            p.id,
            p.date.isoformat(),
            p.amount,
            p.currency,
            p.merchant,
            p.auto_category,
            p.source.value if hasattr(p.source, "value") else str(p.source),
            p.type.value if hasattr(p.type, "value") else str(p.type),
            p.note or "",
            p.category or "",
        ])
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=payments.csv"}
    )

def submit_custom_payment(date, amount, currency, merchant, payment_type, db: Session, user_id: int, source=None, note="", category=""):
    try:
        payment_type_enum = PaymentType(payment_type)
    except Exception:
        raise ValueError("Invalid payment type")

    if source is None:
        payment_source = PaymentSource.OTHER
    else:
        try:
            payment_source = PaymentSource(source)
        except Exception:
            raise ValueError("Invalid payment source")

    import uuid
    payment_id = str(uuid.uuid5(uuid.NAMESPACE_DNS,f"{date.isoformat()}|{amount}|{currency}|{merchant}|{payment_type}|{source}|{note}|{category}|{user_id}"))

    if category:
        valid_categories = set(child_categories(db, user_id))
        if category not in valid_categories:
            raise ValueError(f"Invalid child category: {category}")

    payment = Payment(
        id=payment_id,
        date=date,
        amount=amount,
        currency=currency,
        merchant=merchant,
        auto_category="",
        category=category or "",
        source=payment_source,
        type=payment_type_enum,
        note=note or "",
        user_id=user_id,
    )

    payments = get_all_payments(db, user_id)
    if any(p.id == payment_id for p in payments):
        raise ValueError(f"Payment with id {payment_id} already exists")

    payments.append(payment)
    save_payments(db, payments, user_id)
    return payment

def delete_payments_by_ids(ids: list, db: Session, user_id: int) -> int:
    payments = get_all_payments(db, user_id)
    before = len(payments)
    payments = [p for p in payments if p.id not in ids]
    deleted = before - len(payments)
    if deleted > 0:
        save_payments(db, payments, user_id)
    return deleted

async def import_payment_files_service(files: list, types: list, db: Session, user_id: int) -> dict:
    if not files or len(files) > 3:
        return {"imported": 0, "errors": ["Select 1-3 files."]}
    if not types or len(types) != len(files):
        return {"imported": 0, "errors": ["A type must be specified for each file."]}

    import_funcs = {
        PaymentSource.ALIPAY.value: lambda path: import_alipay_payments(path, db, user_id),
        PaymentSource.WECHAT.value: lambda path: import_wechat_payments(path, db, user_id),
        PaymentSource.TSINGHUA_CARD.value: lambda path: import_tsinghua_card_payments(path, db, user_id),
    }

    imported = 0
    errors = []
    for file, type in zip(files, types):
        if type not in import_funcs:
            errors.append(f"{getattr(file, 'filename', str(file))}: Invalid or unsupported payment type.")
            try:
                file.file.close()
            except Exception:
                pass
            continue
        try:
            filename = getattr(file, "filename", "upload")
            _, ext = os.path.splitext(filename)
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name
            imported += import_funcs[type](tmp_path)
        except Exception as e:
            errors.append(f"{getattr(file, 'filename', str(file))}: {str(e)}")
        finally:
            try:
                file.file.close()
            except Exception:
                pass

    return {"imported": imported, "errors": errors}

def get_sums_for_ranges_service(ranges: Dict[str, Dict[str, Any]], db: Session, user_id: int) -> Dict[str, float]:
    payments = get_all_payments(db, user_id)
    result = {}
    for name, range_dict in ranges.items():
        start = range_dict.get("start")
        end = range_dict.get("end")
        result[name] = sum_payments_in_range(payments, start, end)
    return result

def list_categories(db: Session, user_id: int) -> List[str]:
    return child_categories(db, user_id)

def aggregate_payments_by_category(payments: List[Payment], category_tree: dict, start_date=None, end_date=None):
    return sum_payments_by_category(payments, category_tree, start_date, end_date)

def aggregate_payments_sankey(payments: List[Payment], category_tree: dict, start_date=None, end_date=None):
    result = sum_payments_by_category(payments, category_tree, start_date, end_date)
    sankey_data = build_sankey_data(result, category_tree)
    return sankey_data

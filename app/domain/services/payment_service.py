import csv
import io
import os
import shutil
import tempfile
from typing import Any, Dict, List

from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.data.repositories.payment_repository import add_payment, create_payment_tables
from app.data.repositories.payment_repository import (
    delete_payments_by_ids as repo_delete_payments_by_ids,
)
from app.data.repositories.payment_repository import (
    get_all_child_categories,
    get_all_payments,
    get_category_tree,
    save_category_tree,
)
from app.data.repositories.payment_repository import (
    update_merchant_categories as repo_update_merchant_categories,
)
from app.data.repositories.payment_repository import (
    update_payment_category as repo_update_payment_category,
)
from app.data.repositories.payment_repository import upsert_payments
from app.domain.helpers.aggregation import build_sankey_data, sum_payments_by_category
from app.domain.helpers.sum import sum_payments_in_range
from app.domain.models.payment import Payment, PaymentSource, PaymentType

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
    for p in payments:
        if p.category in deleted_categories:
            if p.id is None:
                raise ValueError(f"Payment with id {p.id} not found")
            update_payment_category(p.id, "", db, user_id)
    save_category_tree(db, user_id, new_tree)


def update_payment_category(
    payment_id: int, cust_category: str, db: Session, user_id: int
) -> None:
    _validate_category(db, user_id, cust_category)
    updated = repo_update_payment_category(db, payment_id, user_id, cust_category)
    if not updated:
        raise ValueError(f"Payment with id {payment_id} not found")


def update_merchant_categories(
    payment_id: int, cust_category: str, db: Session, user_id: int
) -> int:
    _validate_category(db, user_id, cust_category)
    count = repo_update_merchant_categories(db, payment_id, user_id, cust_category)
    if count == 0:
        raise ValueError(f"Payment with id {payment_id} not found")
    return count


def import_alipay_payments(source_filepath: str, db: Session, user_id: int) -> int:
    from app.domain.parsers.alipay_parser import parse_alipay_file

    payments = parse_alipay_file(source_filepath)
    for p in payments:
        p.user_id = user_id
    added = upsert_payments(db, payments, user_id)
    return added


def import_wechat_payments(source_filepath: str, db: Session, user_id: int) -> int:
    from app.domain.parsers.wechat_parser import parse_wechat_file

    payments = parse_wechat_file(source_filepath)
    for p in payments:
        p.user_id = user_id
    added = upsert_payments(db, payments, user_id)
    return added


def import_tsinghua_card_payments(
    source_filepath: str, db: Session, user_id: int
) -> int:
    from app.domain.parsers.tsinghua_card_parser import parse_tsinghua_card_file

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
    writer.writerow(
        [
            "id",
            "date",
            "amount",
            "currency",
            "merchant",
            "auto_category",
            "source",
            "type",
            "note",
            "cust_category",
        ]
    )
    for p in payments:
        writer.writerow(
            [
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
            ]
        )
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=payments.csv"},
    )


def submit_custom_payment(
    date,
    amount,
    currency,
    merchant,
    payment_type,
    db: Session,
    user_id: int,
    source=None,
    note="",
    category="",
):
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

    if category:
        valid_categories = set(child_categories(db, user_id))
        if category not in valid_categories:
            raise ValueError(f"Invalid child category: {category}")

    payment = Payment(
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

    # Use add_payment for efficient DB insert and duplicate check
    return add_payment(db, payment, user_id)


def delete_payments_by_ids(ids: list, db: Session, user_id: int) -> int:
    return repo_delete_payments_by_ids(db, ids, user_id)


async def import_payment_files_service(
    files: list, types: list, db: Session, user_id: int
) -> dict:
    if not files or len(files) > 3:
        return {"imported": 0, "errors": ["Select 1-3 files."]}
    if not types or len(types) != len(files):
        return {"imported": 0, "errors": ["A type must be specified for each file."]}

    import_funcs = {
        PaymentSource.ALIPAY.value: lambda path: import_alipay_payments(
            path, db, user_id
        ),
        PaymentSource.WECHAT.value: lambda path: import_wechat_payments(
            path, db, user_id
        ),
        PaymentSource.TSINGHUA_CARD.value: lambda path: import_tsinghua_card_payments(
            path, db, user_id
        ),
    }

    imported = 0
    errors = []
    for file, type in zip(files, types):
        if type not in import_funcs:
            errors.append(
                f"{getattr(file, 'filename', str(file))}: Unsupported payment type."
            )
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


def get_sums_for_ranges_service(
    ranges: Dict[str, Dict[str, Any]], db: Session, user_id: int
) -> Dict[str, float]:
    payments = get_all_payments(db, user_id)
    result = {}
    for name, range_dict in ranges.items():
        start = range_dict.get("start")
        end = range_dict.get("end")
        result[name] = sum_payments_in_range(payments, start, end)
    return result


def list_categories(db: Session, user_id: int) -> List[str]:
    return child_categories(db, user_id)


def aggregate_payments_by_category(
    payments: List[Payment], category_tree: dict, start_date=None, end_date=None
):
    return sum_payments_by_category(payments, category_tree, start_date, end_date)


def aggregate_payments_sankey(
    payments: List[Payment], category_tree: dict, start_date=None, end_date=None
):
    result, metadata = sum_payments_by_category(
        payments, category_tree, start_date, end_date
    )
    sankey_data = build_sankey_data(result, metadata, category_tree)
    return sankey_data


def add_payments_list(
    payments_data: List[dict], db: Session, user_id: int
) -> List[Payment]:
    """
    Add a list of payments to the database.
    Returns the list of added Payment domain objects.
    """
    added_payments = []
    for data in payments_data:
        payment_type_enum = PaymentType(data["type"])
        payment_source = PaymentSource(data.get("source", PaymentSource.OTHER.value))
        payment = Payment(
            date=data["date"],
            amount=data["amount"],
            currency=data["currency"],
            merchant=data["merchant"],
            auto_category=data.get("auto_category", ""),
            category=data.get("category", ""),
            source=payment_source,
            type=payment_type_enum,
            note=data.get("note", ""),
            user_id=user_id,
        )
        added = add_payment(db, payment, user_id)
        added_payments.append(added)
    return added_payments

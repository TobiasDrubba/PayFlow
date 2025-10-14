import csv
import io
import os
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List

import requests
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.data.repositories.currency_repository import (
    get_currency_rates,
    has_currency_data_for_range,
    set_currency_rates,
    upsert_rates_from_api,
)
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
    payments, _ = get_all_payments(db, user_id)
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


def fetch_and_store_exchange_rates(
    db: Session, start_date: datetime, end_date: datetime
):
    """
    Fetches and stores exchange rates for the given date range if not already present.
    """
    if not has_currency_data_for_range(db, start_date, end_date):
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        url = (
            f"https://api.frankfurter.dev/v1/{start_str}..{end_str}"
            f"?base=CNY&symbols=EUR,USD"
        )
        try:
            response = requests.get(url)
            response.raise_for_status()
            exchange_data = response.json()
            upsert_rates_from_api(db, exchange_data)
        except requests.RequestException as e:
            print(f"Exchange rate API error: {e}")
        except Exception as e:
            print(f"Unexpected error fetching exchange rates: {e}")


def _import_payments_with_parser(
    parser_func, source_filepath: str, db: Session, user_id: int
) -> int:
    payments = parser_func(source_filepath)
    for p in payments:
        p.user_id = user_id

    # Determine earliest and latest payment dates
    dates = [p.date for p in payments if hasattr(p, "date") and p.date]
    if dates:
        earliest = min(dates)
        latest = max(dates)
        fetch_and_store_exchange_rates(db, earliest, latest)
    else:
        raise ValueError("No valid payment dates found in the imported data.")

    return upsert_payments(db, payments, user_id)


def list_payments(
    db: Session,
    user_id: int,
    currency: str | None = None,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
) -> tuple[list[Payment], int]:
    return get_all_payments(db, user_id, currency, page, page_size, search)


def get_payments_csv_stream(db: Session, user_id: int, currency: str | None = None):
    payments, _ = get_all_payments(db, user_id, currency)
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

    # Convert to CNY if currency is EUR or USD
    if currency in ("EUR", "USD"):
        rate_obj = get_currency_rates(db, date)
        euro_rate = rate_obj.EURO if rate_obj else None
        usd_rate = rate_obj.USD if rate_obj else None

        # Fetch from API if missing
        if (currency == "EUR" and euro_rate is None) or (
            currency == "USD" and usd_rate is None
        ):
            api_url = (
                f"https://api.frankfurter.dev/v1/{date.strftime('%Y-%m-%d')}"
                f"?base=CNY&symbols=EUR,USD"
            )
            try:
                response = requests.get(api_url)
                response.raise_for_status()
                data = response.json()
                euro_rate = data["rates"].get("EUR")
                usd_rate = data["rates"].get("USD")
                if euro_rate is None or usd_rate is None:
                    raise ValueError("Exchange rate not found in API response")
                set_currency_rates(db, date, euro_rate, usd_rate)
            except Exception as e:
                raise ValueError(f"Failed to fetch exchange rate: {e}")

        # Calculate amount in CNY by dividing through the rate
        if currency == "EUR":
            rate = euro_rate
            if not euro_rate:
                raise ValueError("EUR exchange rate not available")
        elif currency == "USD":
            rate = usd_rate
            if not usd_rate:
                raise ValueError("USD exchange rate not available")
        else:
            raise ValueError("Unsupported currency")
        amount = amount / rate
        currency = "CNY"

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

    parser_funcs = {
        PaymentSource.ALIPAY.value: lambda: __import__(
            "app.domain.parsers.alipay_parser", fromlist=["parse_alipay_file"]
        ).parse_alipay_file,
        PaymentSource.WECHAT.value: lambda: __import__(
            "app.domain.parsers.wechat_parser", fromlist=["parse_wechat_file"]
        ).parse_wechat_file,
        PaymentSource.TSINGHUA_CARD.value: lambda: __import__(
            "app.domain.parsers.tsinghua_card_parser",
            fromlist=["parse_tsinghua_card_file"],
        ).parse_tsinghua_card_file,
    }

    imported = 0
    errors = []
    for file, type in zip(files, types):
        if type not in parser_funcs:
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
            parser_func = parser_funcs[type]()
            imported += _import_payments_with_parser(parser_func, tmp_path, db, user_id)
        except Exception as e:
            errors.append(f"{getattr(file, 'filename', str(file))}: {str(e)}")
        finally:
            try:
                file.file.close()
            except Exception:
                pass

    return {"imported": imported, "errors": errors}


def get_sums_for_ranges_service(
    ranges: Dict[str, Dict[str, Any]],
    db: Session,
    user_id: int,
    currency: str | None = None,
) -> Dict[str, float]:
    payments, _ = get_all_payments(db, user_id, currency)
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

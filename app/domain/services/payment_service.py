import csv
import io
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from datetime import datetime as _dt
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from fastapi import UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data.repositories.currency_repository import (
    get_currency_rates,
    has_currency_data_for_range,
    set_currency_rates,
    upsert_rates_from_api,
)
from app.data.repositories.payment_repository import (
    update_payments_category_bulk,  # <-- add this import
)
from app.data.repositories.payment_repository import (
    PaymentORM,
    add_payment,
    all_merchant_same_category_db,
    create_payment_tables,
)
from app.data.repositories.payment_repository import (
    delete_payments_by_ids as repo_delete_payments_by_ids,
)
from app.data.repositories.payment_repository import (
    get_all_child_categories,
    get_all_payments,
    get_category_tree,
    save_category_tree,
    sum_payments_by_category_db,
    sum_payments_in_db_range,
)
from app.data.repositories.payment_repository import (
    update_merchant_categories as repo_update_merchant_categories,
)
from app.data.repositories.payment_repository import (
    update_payment_category as repo_update_payment_category,
)
from app.data.repositories.payment_repository import upsert_payments
from app.domain.helpers.aggregation import build_sankey_data
from app.domain.models.payment import Payment, PaymentSource, PaymentType

create_payment_tables()

SUPPORTED_CURRENCIES = {"CNY", "EUR", "USD"}


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
    if deleted_categories:
        # Efficient bulk update in DB layer for deleted categories
        update_payments_category_bulk(db, user_id, list(deleted_categories), "")
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
    sort_field: str = "date",
    sort_direction: str = "desc",
) -> tuple[list[Payment], int]:
    return get_all_payments(
        db, user_id, currency, page, page_size, search, sort_field, sort_direction
    )


def get_payments_csv_stream(db: Session, user_id: int, currency: str | None = None):
    # Fetch all payments without pagination
    payments, _ = get_all_payments(db, user_id, currency, page=1, page_size=10**6)
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
    # Assert currency is valid
    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency: {currency}")

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

    # Ensure the rates are present, else fetch
    rate_obj = get_currency_rates(db, date)
    euro_rate = rate_obj.EURO if rate_obj else None
    usd_rate = rate_obj.USD if rate_obj else None

    # Fetch from API if missing
    if euro_rate is None or usd_rate is None:
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

    # Convert to CNY if currency is EUR or USD
    if currency in ("EUR", "USD"):
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

    if payment_type_enum == PaymentType.EXPENSE and amount > 0:
        amount = -amount

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
    days: int | None = None,
    months: int | None = None,
) -> Dict[str, dict]:
    result = {}
    for name, range_dict in ranges.items():
        start = range_dict.get("start")
        end = range_dict.get("end")
        range_days = range_dict.get("days", days)
        range_months = range_dict.get("months", months)
        start_date = start
        end_date = end

        # Calculate date span based on newest payment
        if range_months is not None and not start and not end:
            newest_payment = (
                db.query(func.max(PaymentORM.date))
                .filter(PaymentORM.user_id == user_id)
                .scalar()
            )
            if newest_payment:
                year = newest_payment.year
                month = newest_payment.month - range_months
                while month <= 0:
                    year -= 1
                    month += 12
                from calendar import monthrange

                first_day = datetime(year, month, 1)
                if range_months == 0:
                    # For current month, end_date is the newest payment's date
                    start_date = first_day
                    end_date = newest_payment
                else:
                    # For past months, end_date is the last day of that month
                    last_day = datetime(
                        year, month, monthrange(year, month)[1], 23, 59, 59, 999999
                    )
                    start_date = first_day
                    end_date = last_day
        # If days is set and start/end not provided, calculate date span
        elif range_days and not start and not end:
            newest_payment = (
                db.query(func.max(PaymentORM.date))
                .filter(PaymentORM.user_id == user_id)
                .scalar()
            )
            if newest_payment:
                end_date = newest_payment
                start_date = end_date - timedelta(days=range_days - 1)

        # If total (start/end both null), get oldest and newest payment dates
        if (
            not start
            and not end
            and not range_days
            and not range_months
            and name == "total"
        ):
            oldest_payment = (
                db.query(func.min(PaymentORM.date))
                .filter(PaymentORM.user_id == user_id)
                .scalar()
            )
            newest_payment = (
                db.query(func.max(PaymentORM.date))
                .filter(PaymentORM.user_id == user_id)
                .scalar()
            )
            start_date = oldest_payment
            end_date = newest_payment

        sum_value = sum_payments_in_db_range(
            db, user_id, start_date, end_date, currency=currency, days=range_days
        )
        result[name] = {
            "sum": sum_value,
            "start_date": start_date,
            "end_date": end_date,
            "days": range_days,
            "months": range_months,
        }
    return result


def list_categories(db: Session, user_id: int) -> List[str]:
    return child_categories(db, user_id)


def aggregate_payments_sankey_db(
    db,
    user_id: int,
    category_tree: dict,
    start_date=None,
    end_date=None,
    currency: str | None = None,
    days: int | None = None,
):
    """
    Efficiently aggregate payments by category using the database layer.
    """
    result, metadata = sum_payments_by_category_db(
        db, user_id, category_tree, start_date, end_date, currency, days
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
        # Assert currency is valid
        if data["currency"] not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {data['currency']}")
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


def all_merchant_same_category_service(
    db: Session, user_id: int, merchant: str, cust_category: str
) -> bool:
    return all_merchant_same_category_db(db, user_id, merchant, cust_category)


# In-memory cache:
# key = username (derived from recipient or sender), value = list of metadata dicts
MAILGUN_ATTACHMENT_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def _derive_username_from_recipient(recipient: Optional[str]) -> str:
    if not recipient:
        return "unknown_user"
    primary = str(recipient).split(",")[0].strip()
    username = primary.split("@")[0] if "@" in primary else primary
    username = username.split("+")[0]
    return username


def _derive_cache_username_from_user(current_user: Any) -> str:
    candidate = getattr(current_user, "email", None) or getattr(
        current_user, "username", None
    )
    if candidate:
        s = str(candidate)
        if "@" in s:
            local = s.split(",")[0].strip().split("@")[0]
            return local.split("+")[0]
        return s
    uid = getattr(current_user, "id", None)
    return f"user_{uid}" if uid is not None else "unknown_user"


def cache_mailgun_form_attachments(form) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Process a Mailgun inbound multipart form, persist file attachments to temp files,
    and cache metadata in MAILGUN_ATTACHMENT_CACHE.

    Returns (username, saved_metadata_list).

    Raises ValueError if no attachments found.
    """
    recipient = (
        form.get("recipient") or form.get("to") or form.get("To") or form.get("sender")
    )
    username = _derive_username_from_recipient(recipient)

    saved = []
    for key, value in form.multi_items():
        if hasattr(value, "filename") and value.filename:
            upload: UploadFile = value  # type: ignore
            filename = upload.filename
            try:
                _, ext = os.path.splitext(filename)
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    try:
                        shutil.copyfileobj(upload.file, tmp)
                    finally:
                        try:
                            upload.file.close()
                        except Exception:
                            pass
                    tmp_path = tmp.name

                meta = {
                    "filename": filename,
                    "path": tmp_path,
                    "content_type": getattr(upload, "content_type", None),
                    "received_at": _dt.utcnow(),
                    "mailgun_field": key,
                }
                saved.append(meta)
            except Exception:
                # Continue on individual file errors
                continue

    if not saved:
        raise ValueError("No attachments found in Mailgun POST")

    MAILGUN_ATTACHMENT_CACHE.setdefault(username, []).extend(saved)
    return username, saved


def get_mailgun_cached_files_for_user(current_user: Any) -> Dict[str, Any]:
    """
    Return sanitized cached metadata for a given user object (suitable for frontend).
    Does not expose filesystem paths.
    """
    username = _derive_cache_username_from_user(current_user)
    entries = MAILGUN_ATTACHMENT_CACHE.get(username, [])
    files = []
    for m in entries:
        received = m.get("received_at")
        if not received:
            received = "unknown"
        files.append(
            {
                "filename": m.get("filename"),
                "content_type": m.get("content_type"),
                "received_at": received.isoformat()
                if hasattr(received, "isoformat")
                else str(received),
                "mailgun_field": m.get("mailgun_field"),
            }
        )
    return {"username": username, "cached_files": len(entries), "files": files}


# New: import cached mailgun zips, unzip with passwords and import extracted files
async def import_cached_mailgun_zips(
    items: Iterable[Any], db: Session, current_user: Any
) -> Dict[str, Any]:
    """
    items: iterable of dict-like objects with keys: filename, password (optional), type
    Returns: {"imported": int, "errors": [str,...]}
    """
    username = _derive_cache_username_from_user(current_user)
    errors: List[str] = []
    wrappers: List[Any] = []  # objects with .file and .filename
    types_list: List[str] = []
    tmpdirs: List[str] = []
    processed_cache_entries: List[Dict[str, Any]] = []

    if not items:
        return {"imported": 0, "errors": ["No items provided"]}

    cache_list = MAILGUN_ATTACHMENT_CACHE.get(username, [])

    for raw_item in items:
        # accept plain dicts or Pydantic-like objects (fallback to attribute access)
        if isinstance(raw_item, dict):
            item = raw_item
        else:
            # try model_dump() if available, else fallback to getattr
            if hasattr(raw_item, "model_dump"):
                item = raw_item.model_dump()
            else:
                # build a small dict from common attrs
                item = {
                    "filename": getattr(raw_item, "filename", None),
                    "password": getattr(raw_item, "password", None),
                    "type": getattr(raw_item, "type", None),
                }

        fname = item.get("filename")
        pwd = item.get("password") or ""
        ptype = item.get("type")
        if not fname or not ptype:
            errors.append(f"{fname or '<unknown>'}: missing filename or type")
            continue

        # Find a matching cached entry by filename
        match = None
        for e in cache_list:
            if e.get("filename") == fname:
                match = e
                break
        if not match:
            errors.append(f"{fname}: not found in cache")
            continue

        zip_path = match.get("path")
        if not zip_path or not os.path.exists(zip_path):
            errors.append(f"{fname}: cached file missing on disk")
            continue

        # Extract into temp dir using provided password (if any)
        tmpdir = tempfile.mkdtemp()
        tmpdirs.append(tmpdir)
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                try:
                    pwd_bytes = bytes(pwd, "utf-8") if pwd else None
                    if pwd_bytes:
                        zf.extractall(tmpdir, pwd=pwd_bytes)
                    else:
                        zf.extractall(tmpdir)
                except RuntimeError:
                    errors.append(f"{fname}: failed to unzip (bad password)")
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    tmpdirs.pop()
                    continue
                except zipfile.BadZipFile:
                    errors.append(f"{fname}: not a zip or corrupted")
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    tmpdirs.pop()
                    continue

            # Walk extracted files and prepare wrappers
            any_extracted = False
            for root, _, filenames in os.walk(tmpdir):
                for file in filenames:
                    any_extracted = True
                    fp = os.path.join(root, file)
                    try:
                        fobj = open(fp, "rb")
                    except Exception as e:
                        errors.append(
                            f"{fname}: failed to open extracted file {file}: {e}"
                        )
                        continue
                    wrappers.append(SimpleNamespace(file=fobj, filename=file))
                    types_list.append(ptype)

            if not any_extracted:
                errors.append(f"{fname}: zip opened but no files extracted")
                # keep tmpdir for cleanup loop
                continue

            # Mark for removal from cache on successful import later
            processed_cache_entries.append(match)
        except Exception as e:
            errors.append(f"{fname}: unzip error: {e}")
            shutil.rmtree(tmpdir, ignore_errors=True)
            if tmpdir in tmpdirs:
                tmpdirs.remove(tmpdir)
            continue

    if not wrappers:
        # No files prepared for import
        return {"imported": 0, "errors": errors}

    # Use existing import logic (async)
    try:
        import_result = await import_payment_files_service(
            wrappers, types_list, db, current_user.id
        )
    except Exception as e:
        # Ensure we close wrapper files and cleanup tmpdirs
        for w in wrappers:
            try:
                w.file.close()
            except Exception:
                pass
        for td in tmpdirs:
            shutil.rmtree(td, ignore_errors=True)
        return {"imported": 0, "errors": errors + [f"Import internal error: {e}"]}

    # Close wrapper files and cleanup extracted tmpdirs
    for w in wrappers:
        try:
            w.file.close()
        except Exception:
            pass
    for td in tmpdirs:
        shutil.rmtree(td, ignore_errors=True)

    # Merge errors returned from import_result
    imported = import_result.get("imported", 0)
    import_errors = import_result.get("errors", []) or []
    errors.extend(import_errors)

    # If some imports succeeded, remove from cache and delete zip files
    if imported > 0 and processed_cache_entries:
        remaining = MAILGUN_ATTACHMENT_CACHE.get(username, [])
        for entry in processed_cache_entries:
            try:
                if entry in remaining:
                    remaining.remove(entry)
                path = entry.get("path")
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            except Exception:
                pass
        # update or remove cache key
        if remaining:
            MAILGUN_ATTACHMENT_CACHE[username] = remaining
        else:
            MAILGUN_ATTACHMENT_CACHE.pop(username, None)

    return {"imported": imported, "errors": errors}

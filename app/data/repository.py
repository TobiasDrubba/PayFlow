# app/data/repository.py
import csv
from pathlib import Path
from datetime import datetime
from typing import List
from dotenv import load_dotenv
import os

from app.domain.models import Payment, PaymentSource, PaymentType

load_dotenv()
CSV_HEADER = ["id", "date", "amount", "currency", "merchant", "auto_category", "source", "type", "note", "cust_category"]
FILE_PATH = os.getenv("PAYMENTS_CSV_PATH")

def load_payments_from_csv(csv_path: str) -> List[Payment]:
    """
    Load payments from a CSV file if it exists.
    Returns an empty list if the file doesn't exist or is empty.
    """
    path = Path(csv_path)
    if not path.exists() or path.stat().st_size == 0:
        return []

    payments: List[Payment] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            payments.append(
                Payment(
                    id=row["id"],
                    date=datetime.strptime(row["date"], "%Y-%m-%d %H:%M:%S"),
                    amount=float(row["amount"]),
                    currency=row["currency"],
                    merchant=row["merchant"],
                    auto_category=row.get("auto_category", "") or "",
                    cust_category=row.get("cust_category", "") or "",
                    source=PaymentSource(row["source"]) if row.get("source") else PaymentSource.OTHER,
                    type=PaymentType(row["type"]) if row.get("type") else PaymentType.NONE,
                    note=row.get("note", "") or "",
                )
            )
    return payments


def save_payments_to_csv(csv_path: str, payments: List[Payment]) -> None:
    """
    Save all payments to a CSV file (overwrites).
    Dates are stored in YYYY-MM-DD HH:MM:SS format.
    """
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        for p in payments:
            writer.writerow(
                {
                    "id": p.id,
                    "date": p.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "amount": f"{p.amount:.2f}",
                    "currency": p.currency,
                    "merchant": p.merchant,
                    "auto_category": p.auto_category,
                    "source": p.source.value,
                    "type": p.type.value if hasattr(p, "type") else PaymentType.NONE.value,
                    "note": p.note,
                    "cust_category": p.cust_category,
                }
            )


def upsert_payments_to_csv(incoming: List[Payment]) -> int:
    """
    Append only non-existing payments (by unique id) to the CSV and persist it.
    Returns the number of newly added payments.
    """
    existing = load_payments_from_csv(FILE_PATH)
    existing_ids = {p.id for p in existing}

    new_items = [p for p in incoming if p.id not in existing_ids]
    if not new_items:
        return 0

    combined = existing + new_items
    combined.sort(key=lambda p: p.date, reverse=True)

    save_payments_to_csv(FILE_PATH, combined)
    return len(new_items)


def get_all_payments() -> List[Payment]:
    """
    Repository method to return all payments from persistent storage (CSV).
    """
    return load_payments_from_csv(FILE_PATH)

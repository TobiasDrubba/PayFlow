# app/data/repository.py
import csv
from pathlib import Path
from datetime import datetime
from typing import List
from dotenv import load_dotenv
import os
import json

from app.domain.models import Payment, PaymentSource, PaymentType

load_dotenv()
CSV_HEADER = ["id", "date", "amount", "currency", "merchant", "auto_category", "source", "type", "note", "cust_category"]
FILE_PATH = os.getenv("PAYMENTS_CSV_PATH")
if not FILE_PATH:
    raise RuntimeError("PAYMENTS_CSV_PATH environment variable is not set")

CATEGORIES_JSON_PATH = os.getenv("CATEGORIES_JSON_PATH")
if not CATEGORIES_JSON_PATH:
    raise RuntimeError("CATEGORIES_JSON_PATH environment variable is not set")


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
                    category=row.get("cust_category", "") or "",
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
                    "cust_category": p.category,
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


def load_category_tree() -> dict:
    """
    Load the category tree from JSON file.
    """
    path = Path(CATEGORIES_JSON_PATH)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_category_tree(tree: dict) -> None:
    """
    Save the category tree to JSON file.
    """
    path = Path(CATEGORIES_JSON_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)


def get_all_child_categories(tree: dict = None) -> list:
    """
    Return all child categories (flattened, no parents).
    Supports leaves as:
      - strings inside lists (e.g., "Food and Drinks": ["Food", "Drink"])
      - keys in dicts with null values (e.g., "Transportation": {"Taxi": null})
    """
    if tree is None:
        tree = load_category_tree()
    result = set()

    def collect(node):
        if isinstance(node, dict):
            for k, v in node.items():
                # If value is None, treat the key as a leaf category
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

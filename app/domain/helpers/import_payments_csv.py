import csv
from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from app.data.base import engine
from app.data.repositories.payment_repository import upsert_payments
from app.domain.models.payment import Payment, PaymentSource, PaymentType

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def parse_csv_payments(csv_path, user_id):
    payments = []
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                payment = Payment(
                    date=datetime.fromisoformat(row["date"]),
                    amount=float(row["amount"]),
                    currency=row["currency"],
                    merchant=row["merchant"],
                    auto_category=row.get("auto_category", ""),
                    source=PaymentSource(row["source"]),
                    type=PaymentType(row["type"]),
                    note=row.get("note", ""),
                    category=row.get("cust_category", ""),
                    user_id=user_id,
                )
                payments.append(payment)
            except Exception as e:
                print(f"Skipping row due to error: {e}\nRow: {row}")
    return payments


def import_payments_from_csv(
    csv_path: str, user_id: int, api_url: str | None = None, token: str | None = None
):
    payments = parse_csv_payments(csv_path, user_id)
    if api_url:
        import requests

        # Prepare payload for API
        payload = {
            "payments": [
                {
                    "date": p.date.isoformat(),
                    "amount": p.amount,
                    "currency": p.currency,
                    "merchant": p.merchant,
                    "type": p.type.value,
                    "source": p.source.value,
                    "note": p.note,
                    "category": p.category,
                }
                for p in payments
            ]
        }
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            resp = requests.post(api_url, json=payload, headers=headers)
            resp.raise_for_status()
            print(
                f"Sent {len(payments)} payments to API {api_url}."
                f" Response: {resp.status_code}"
            )
        except Exception as e:
            print(f"Failed to send payments to API: {e}")
    else:
        db: Session = SessionLocal()
        try:
            count = upsert_payments(db, payments, user_id)
            print(f"Imported {count} payments for user_id={user_id}")
        finally:
            db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import payments from CSV.")
    parser.add_argument("csv_path", help="Path to CSV file")
    parser.add_argument("user_id", type=int, help="User ID")
    parser.add_argument(
        "--api-url", help="API endpoint to POST payments batch (optional)", default=None
    )
    parser.add_argument(
        "--token", help="Bearer token for API authentication (optional)", default=None
    )
    args = parser.parse_args()

    import_payments_from_csv(
        args.csv_path, args.user_id, api_url=args.api_url, token=args.token
    )

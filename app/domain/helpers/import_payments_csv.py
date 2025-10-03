import csv
import sys
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


def import_payments_from_csv(csv_path: str, user_id: int):
    payments = parse_csv_payments(csv_path, user_id)
    db: Session = SessionLocal()
    try:
        count = upsert_payments(db, payments, user_id)
        print(f"Imported {count} payments for user_id={user_id}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m app.utils.import_payments_csv <csv_path> <user_id>")
        sys.exit(1)
    csv_path = sys.argv[1]
    user_id = int(sys.argv[2])
    import_payments_from_csv(csv_path, user_id)

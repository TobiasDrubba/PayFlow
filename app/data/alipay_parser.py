# app/data/alipay_parser.py
import csv
from datetime import datetime
from typing import List
from app.domain.models import Payment, PaymentSource

# 🔧 Define your column numbers here (0-based index)
DATE_COL = 0           # e.g., "2025-09-22 12:58:10"
MERCHANT_COL = 2       # e.g., "Merchant Name"
DETAILS_COL = 4        # (Optional) description column, could be used as note
TRANSACTION_ID_COL = 9  # example index for transaction ID
AMOUNT_COL = 6         # e.g., "5.40"
CATEGORY_COL = 1       # (Optional) 收/支 (income/expense)

def parse_alipay_file(filepath: str) -> List[Payment]:
    """
    Reads an Alipay TSV file and returns a list of Payment objects.
    Adjust the column numbers above if your file format changes.
    """
    payments = []
    with open(filepath, "r", encoding="gb18030") as f:
        reader = csv.reader(f, delimiter=",")
        rows = list(reader)

    # Find the first row that looks like data
    data_start = 0
    for i, row in enumerate(rows):
        if len(row) > DATE_COL and row[DATE_COL][:4].isdigit() and "-" in row[DATE_COL]:
            data_start = i
            break

    for row in rows[data_start:]:
        if len(row) <= max(DATE_COL, AMOUNT_COL, MERCHANT_COL, TRANSACTION_ID_COL):
            continue  # skip malformed rows
        try:
            payment = Payment(
                id=row[TRANSACTION_ID_COL],
                date=datetime.strptime(row[DATE_COL], "%Y-%m-%d %H:%M:%S"),
                amount=float(row[AMOUNT_COL]),
                currency="CNY",
                merchant=row[MERCHANT_COL],
                category=row[CATEGORY_COL] if len(row) > CATEGORY_COL else "Uncategorized",
                source=PaymentSource.ALIPAY,
                note=row[DETAILS_COL] if len(row) > DETAILS_COL else ""
            )
            payments.append(payment)
        except Exception as e:
            print(f"Skipping row due to parsing error: {e}")

    return payments


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.data.alipay_parser <filepath>")
    else:
        filepath = sys.argv[1]
        payments = parse_alipay_file(filepath)
        for p in payments:
            print(p)

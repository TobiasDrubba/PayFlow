# app/data/other_parser.py
import csv
from datetime import datetime
from typing import List

from app.domain.models.payment import Payment, PaymentSource, PaymentType

# 🔧 Define your column numbers here (0-based index)
DATE_COL = 0  # e.g., "2025-09-22 12:58:10"
MERCHANT_COL = 1  # e.g., "Merchant Name"
AMOUNT_COL = 2  # e.g., "5.40"
CURRENCY_COL = 3  # e.g. CNY, etc. except for EURO all should have three letters
TYP_COL = 4  # income/expense
DETAILS_COL = 5  # (Optional) description column, could be used as note
CATEGORY_COL = 6  # (Optional) Supposed Category


def parse_other_file(filepath: str) -> List[Payment]:
    """
    Reads an other TSV file and returns a list of Payment objects.
    Adjust the column numbers above if your file format changes.
    """
    payments = []
    with open(filepath, "r") as f:
        reader = csv.reader(f, delimiter=",")
        rows = list(reader)

    # Find the first row that looks like data
    data_start = 0
    for i, row in enumerate(rows):
        if len(row) > DATE_COL and row[DATE_COL][:4].isdigit() and "-" in row[DATE_COL]:
            data_start = i
            break

    for row in rows[data_start:]:
        if len(row) <= max(DATE_COL, AMOUNT_COL, MERCHANT_COL):
            continue  # skip malformed rows
        try:
            amount = float(row[AMOUNT_COL])
            cat = row[CATEGORY_COL] if len(row) > CATEGORY_COL else "Uncategorized"
            raw_cat = row[TYP_COL].strip().lower() if len(row) > TYP_COL else ""
            if "income" in raw_cat or "收入" in raw_cat:
                p_type = PaymentType.INCOME
            elif "expense" in raw_cat or "支出" in raw_cat:
                p_type = PaymentType.EXPENSE
                amount *= -1
            else:
                # Check if transaction is abort or refund
                if "refund" in cat or "退款" in cat:
                    p_type = PaymentType.REFUND
                else:
                    p_type = PaymentType.ABORT

            payment = Payment(
                date=datetime.strptime(row[DATE_COL], "%Y-%m-%d %H:%M:%S"),
                amount=amount,
                currency=row[CURRENCY_COL],
                merchant=row[MERCHANT_COL],
                auto_category=cat,
                source=PaymentSource.OTHER,
                type=p_type,
                note=row[DETAILS_COL] if len(row) > DETAILS_COL else "",
            )
            payments.append(payment)
        except Exception as e:
            print(f"Skipping row due to parsing error: {e}")

    return payments


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.data.other_parser <filepath>")
    else:
        filepath = sys.argv[1]
        payments = parse_other_file(filepath)
        for p in payments:
            print(p)

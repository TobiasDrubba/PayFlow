# app/data/wechat_parser.py
import openpyxl
from datetime import datetime
from typing import List
from app.domain.models import Payment, PaymentSource, PaymentType

# Define your column numbers here (0-based index)
DATE_COL = 0
MERCHANT_COL = 2
DETAILS_COL = 3
TRANSACTION_ID_COL = 8
AMOUNT_COL = 5
# not existing: CATEGORY_COL = 1
TYP_COL = 4

def parse_wechat_file(filepath: str) -> List[Payment]:
    """
    Reads a WeChat .xlsx file and returns a list of Payment objects.
    Adjust the column numbers above if your file format changes.
    """
    payments = []
    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    # Find the first row that looks like data
    data_start = 0
    for i, row in enumerate(rows):
        if row and isinstance(row[DATE_COL], str) and row[DATE_COL][:4].isdigit() and "-" in row[DATE_COL]:
            data_start = i
            break

    for row in rows[data_start:]:
        if len(row) <= max(DATE_COL, AMOUNT_COL, MERCHANT_COL, TRANSACTION_ID_COL):
            continue  # skip malformed rows
        try:
            amount = float(row[AMOUNT_COL][1:])
            raw_cat = str(row[TYP_COL]).strip().lower() if row[TYP_COL] else ""
            if "income" in raw_cat or "收入" in raw_cat:
                p_type = PaymentType.INCOME
            elif "expense" in raw_cat or "支出" in raw_cat:
                p_type = PaymentType.EXPENSE
            else:
                raise ValueError("Transaction type is not recognized.")

            payment = Payment(
                date=datetime.strptime(row[DATE_COL], "%Y-%m-%d %H:%M:%S"),
                amount=amount,
                currency="CNY",
                merchant=row[MERCHANT_COL],
                source=PaymentSource.WECHAT,
                type=p_type,
                note=row[DETAILS_COL] if row[DETAILS_COL] else ""
            )
            payments.append(payment)
        except Exception as e:
            print(f"Skipping row due to parsing error: {e}")

    return payments

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.data.wechat_parser <filepath>")
    else:
        filepath = sys.argv[1]
        payments = parse_wechat_file(filepath)
        for p in payments:
            print(p)

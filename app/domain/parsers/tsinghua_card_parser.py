# app/data/tsinghua_card_parser.py
from datetime import datetime
from typing import List

import openpyxl

from app.domain.models.payment import Payment, PaymentSource, PaymentType

# Define your column numbers here (0-based index)
DATE_COL = 2
MERCHANT_COL = 0
DETAILS_COL = 4  # Card Balance
TRANSACTION_ID_COL = 2
AMOUNT_COL = 1
# not existing: CATEGORY_COL = 1
TYP_COL = 3


def parse_tsinghua_card_file(filepath: str) -> List[Payment]:
    """
    Reads a tsinghua_card .xlsx file and returns a list of Payment objects.
    Adjust the column numbers above if your file format changes.
    """
    payments = []
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    # Find the first row that looks like data
    data_start = 0
    for i, row in enumerate(rows):
        if i < 3:  # Skip the first rows which are headers
            continue
        if (
            row
            and isinstance(row[DATE_COL], str)
            and row[DATE_COL][:4].isdigit()
            and "-" in row[DATE_COL]
        ):
            data_start = i
            break

    for row in rows[data_start:]:
        if len(row) <= max(DATE_COL, AMOUNT_COL, MERCHANT_COL, TRANSACTION_ID_COL):
            continue  # skip malformed rows
        try:
            amount = float(row[AMOUNT_COL])
            raw_cat = str(row[TYP_COL]).strip().lower() if row[TYP_COL] else ""
            if "微信充值" in raw_cat:
                p_type = PaymentType.INCOME
            elif "持卡人消费" in raw_cat:
                p_type = PaymentType.EXPENSE
                amount *= -1
            else:
                raise ValueError("Transaction type is not recognized.")
            # Determine the category based on the time of day.

            hour = datetime.strptime(row[DATE_COL], "%Y-%m-%d %H:%M:%S").hour
            if p_type == PaymentType.INCOME:
                cust_category = "Card Recharge"
            elif 5 <= hour < 11:
                cust_category = "Canteen Breakfast"
            elif 11 <= hour < 16:
                cust_category = "Canteen Lunch"
            elif 16 <= hour < 24:
                cust_category = "Canteen Dinner"
            else:
                raise ValueError("Transaction time is outside expected range.")
            payment = Payment(
                date=datetime.strptime(row[DATE_COL], "%Y-%m-%d %H:%M:%S"),
                amount=amount,
                currency="CNY",
                merchant=row[MERCHANT_COL],
                source=PaymentSource.TSINGHUA_CARD,
                type=p_type,
                note="Remaining Balance: " + row[DETAILS_COL]
                if row[DETAILS_COL]
                else "",
                category=cust_category,
            )
            payments.append(payment)
        except Exception as e:
            print(f"Skipping row due to parsing error: {e}")

    return payments


if __name__ == "__main__":
    import sys

    def plot_payment_times(payments):
        import matplotlib.pyplot as plt

        times = [p.date.hour + p.date.minute / 60.0 for p in payments]
        plt.figure(figsize=(10, 2))
        plt.scatter(times, [1] * len(times), alpha=0.6)
        plt.yticks([])
        plt.xlabel("Time of Day (Hour)")
        plt.title("Distribution of Payment Times")
        plt.xlim(0, 24)
        plt.tight_layout()
        plt.show()

    if len(sys.argv) < 2:
        print("Usage: python -m app.data.tsinghua_card_parser <filepath> [-p]")
    else:
        filepath = sys.argv[1]
        show_plot = "-p" in sys.argv
        payments = parse_tsinghua_card_file(filepath)
        for p in payments:
            print(p)
        if show_plot:
            plot_payment_times(payments)

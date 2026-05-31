import csv
from datetime import datetime
from typing import List

from app.domain.models.payment import Payment, PaymentSource, PaymentType

# DKB CSV columns (0-based index, semicolon-delimited)
DATE_COL = 0  # Buchungsdatum
VALUE_DATE_COL = 1  # Wertstellung
STATUS_COL = 2  # Status
PAYER_COL = 3  # Zahlungspflichtiger (merchant for Eingang)
PAYEE_COL = 4  # Zahlungsempfängerin (merchant for Ausgang)
DETAILS_COL = 5  # Verwendungszweck
TYP_COL = 6  # Umsatztyp (Eingang/Ausgang)
IBAN_COL = 7  # IBAN
AMOUNT_COL = 8  # Betrag (€)
CREDITOR_ID_COL = 9  # Gläubiger-ID
MANDATE_REF_COL = 10  # Mandatsreferenz
CUSTOMER_REF_COL = 11  # Kundenreferenz


def _parse_german_amount(raw: str) -> float:
    s = raw.strip().strip('"').replace("€", "").strip()
    if not s:
        raise ValueError("Empty amount")
    s = s.replace(".", "").replace(",", ".")
    return float(s)


def _parse_dkb_date(raw: str) -> datetime:
    s = raw.strip().strip('"')
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {raw!r}")


def _looks_like_dkb_date(value: str) -> bool:
    s = value.strip().strip('"')
    return len(s) >= 8 and s[2] == "." and s[5] == "." and s[:2].isdigit()


def _merchant_for_type(row: list[str], p_type: PaymentType) -> str:
    if p_type == PaymentType.EXPENSE:
        merchant = row[PAYEE_COL].strip().strip('"') if len(row) > PAYEE_COL else ""
    else:
        merchant = row[PAYER_COL].strip().strip('"') if len(row) > PAYER_COL else ""
    return merchant or "Unknown"


def parse_dkb_file(filepath: str) -> List[Payment]:
    """
    Reads a DKB semicolon-separated CSV export and returns Payment objects.
    """
    payments = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        rows = list(reader)

    data_start = 0
    for i, row in enumerate(rows):
        if not row:
            continue
        first = row[0].strip().strip('"').lower()
        if first == "buchungsdatum":
            data_start = i + 1
            break
        if len(row) > DATE_COL and _looks_like_dkb_date(row[DATE_COL]):
            data_start = i
            break

    for row in rows[data_start:]:
        if len(row) <= max(DATE_COL, AMOUNT_COL, TYP_COL):
            continue
        if not _looks_like_dkb_date(row[DATE_COL]):
            continue
        try:
            amount = abs(_parse_german_amount(row[AMOUNT_COL]))
            raw_typ = (
                row[TYP_COL].strip().strip('"').lower() if len(row) > TYP_COL else ""
            )
            if "eingang" in raw_typ:
                p_type = PaymentType.INCOME
            elif "ausgang" in raw_typ:
                p_type = PaymentType.EXPENSE
                amount *= -1
            else:
                print(f"Skipping row with unrecognized Umsatztyp: {row[TYP_COL]!r}")
                continue

            note = row[DETAILS_COL].strip().strip('"') if len(row) > DETAILS_COL else ""
            extra_parts = []
            for col_idx, label in (
                (IBAN_COL, "IBAN"),
                (CREDITOR_ID_COL, "Gläubiger-ID"),
                (MANDATE_REF_COL, "Mandatsreferenz"),
                (CUSTOMER_REF_COL, "Kundenreferenz"),
            ):
                if len(row) > col_idx:
                    value = row[col_idx].strip().strip('"')
                    if value:
                        extra_parts.append(f"{label}: {value}")
            if extra_parts:
                note = (
                    " | ".join([note] + extra_parts)
                    if note
                    else " | ".join(extra_parts)
                )

            payment = Payment(
                date=_parse_dkb_date(row[DATE_COL]),
                amount=amount,
                currency="EURO",
                merchant=_merchant_for_type(row, p_type),
                source=PaymentSource.DKB,
                type=p_type,
                note=note,
            )
            payments.append(payment)
        except Exception as e:
            print(f"Skipping row due to parsing error: {e}")

    return payments


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.domain.parsers.dkb_parser <filepath>")
    else:
        filepath = sys.argv[1]
        parsed = parse_dkb_file(filepath)
        for p in parsed:
            print(p)

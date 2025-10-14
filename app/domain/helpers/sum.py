from datetime import datetime
from typing import List, Optional

from app.domain.models.payment import Payment, PaymentType


def get_signed_amount(payment: Payment) -> float:
    """
    Returns the signed amount for a payment depending on its type.
    EXPENSE: negative, INCOME/REFUND: positive, ABORT/other: zero.
    """
    if payment.type == PaymentType.ABORT:
        return 0.0
    return payment.amount


def sum_payments_in_range(
    payments: List[Payment], start: Optional[datetime], end: Optional[datetime]
) -> float:
    total = 0.0
    # Convert start/end to date if provided
    start_date = start.date() if start else None
    end_date = end.date() if end else None
    for p in payments:
        p_date = p.date.date() if isinstance(p.date, datetime) else p.date
        if start_date and p_date < start_date:
            continue
        if end_date and p_date > end_date:
            continue
        total += get_signed_amount(p)
    return total

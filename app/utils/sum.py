from typing import List, Optional
from datetime import datetime
from app.domain.models import Payment, PaymentType

def get_signed_amount(payment: Payment) -> float:
    """
    Returns the signed amount for a payment depending on its type.
    EXPENSE: negative, INCOME/REFUND: positive, ABORT/other: zero.
    """
    if payment.type == PaymentType.ABORT:
        return 0.0
    if payment.type == PaymentType.EXPENSE:
        return -payment.amount
    elif payment.type in (PaymentType.INCOME, PaymentType.REFUND):
        return payment.amount
    return 0.0

def sum_payments_in_range(payments: List[Payment], start: Optional[datetime], end: Optional[datetime]) -> float:
    total = 0.0
    for p in payments:
        if start and p.date < start:
            continue
        if end and p.date > end:
            continue
        total += get_signed_amount(p)
    return total

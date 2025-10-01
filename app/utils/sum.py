from typing import List, Optional
from datetime import datetime
from app.domain.models import Payment, PaymentType

def sum_payments_in_range(payments: List[Payment], start: Optional[datetime], end: Optional[datetime]) -> float:
    total = 0.0
    for p in payments:
        if start and p.date < start:
            continue
        if end and p.date > end:
            continue
        if p.type == PaymentType.ABORT:
            continue
        if p.type == PaymentType.EXPENSE:
            total -= p.amount
        elif p.type in (PaymentType.INCOME, PaymentType.REFUND):
            total += p.amount
        # ignore other types
    return total

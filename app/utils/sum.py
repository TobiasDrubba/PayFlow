from typing import List, Optional
from datetime import datetime
from app.domain.models import Payment

def sum_payments_in_range(payments: List[Payment], start: Optional[datetime], end: Optional[datetime]) -> float:
    total = 0.0
    for p in payments:
        if start and p.date < start:
            continue
        if end and p.date > end:
            continue
        total += p.amount
    return total


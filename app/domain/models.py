# app/domain/models.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PaymentSource(Enum):
    ALIPAY = "Alipay"
    WECHAT = "WeChat Pay"
    OTHER = "Other"


@dataclass
class Payment:
    id: str
    date: datetime
    amount: float
    currency: str
    merchant: str
    category: str
    source: PaymentSource
    note: str = ""

    def __post_init__(self):
        # Basic validation
        if self.amount == 0:
            raise ValueError("Payment amount cannot be zero.")
        if not self.currency:
            raise ValueError("Currency must be provided.")

# app/domain/models.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PaymentSource(Enum):
    ALIPAY = "Alipay"
    WECHAT = "WeChat"
    OTHER = "Other"

class PaymentType(Enum):
    INCOME = "income"
    EXPENSE = "expense"
    ABORT = "abort"
    REFUND = "refund"
    NONE = "none"

@dataclass
class Payment:
    id: str
    date: datetime
    amount: float
    currency: str
    merchant: str
    auto_category: str
    source: PaymentSource
    type: PaymentType = PaymentType.NONE
    note: str = ""
    cust_category: str = ""

    def __post_init__(self):
        # Basic validation
        if self.amount == 0:
            raise ValueError("Payment amount cannot be zero.")
        if not self.currency:
            raise ValueError("Currency must be provided.")

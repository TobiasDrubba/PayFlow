# app/domain/models.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class PaymentSource(Enum):
    ALIPAY = "Alipay"
    WECHAT = "WeChat"
    TSINGHUA_CARD = "Tsinghua Card"
    OTHER = "Other"

class PaymentType(Enum):
    INCOME = "income"
    EXPENSE = "expense"
    ABORT = "abort"
    REFUND = "refund"

@dataclass
class Payment:
    id: str
    date: datetime
    amount: float
    currency: str
    merchant: str
    source: PaymentSource
    type: PaymentType
    note: str = ""
    category: str = ""
    auto_category: str = "Uncategorized"
    user_id: int = None  # New: associate payment with user

    def __post_init__(self):
        # Basic validation
        if self.amount == 0:
            raise ValueError("Payment amount cannot be zero.")
        if not self.currency:
            raise ValueError("Currency must be provided.")

@dataclass
class User:
    id: int
    username: str
    hashed_password: str

@dataclass
class CategoryTree:
    id: int
    user_id: int
    tree_json: str

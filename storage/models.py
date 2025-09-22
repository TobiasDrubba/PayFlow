from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import csv
import os
from pathlib import Path


@dataclass
class Transaction:
    """Primary data model for transaction records"""
    transaction_id: str
    timestamp: datetime
    description: str
    amount: float
    currency: str
    transaction_type: str  # 'income' or 'expense'
    source: str  # 'wechat' or 'alipay'
    
    def to_dict(self) -> dict:
        """Convert transaction to dictionary for CSV writing"""
        return {
            'transaction_id': self.transaction_id,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'amount': self.amount,
            'currency': self.currency,
            'transaction_type': self.transaction_type,
            'source': self.source
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        """Create transaction from dictionary (CSV reading)"""
        return cls(
            transaction_id=data['transaction_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            description=data['description'],
            amount=float(data['amount']),
            currency=data['currency'],
            transaction_type=data['transaction_type'],
            source=data['source']
        )
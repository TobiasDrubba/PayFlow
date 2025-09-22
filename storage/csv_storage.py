import csv
import os
from pathlib import Path
from typing import List, Optional
from .models import Transaction


class TransactionStorage:
    """CSV-based storage layer for transactions"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.csv_file = self.data_dir / "transactions.csv"
        self._ensure_data_dir()
        self._ensure_csv_header()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        self.data_dir.mkdir(exist_ok=True)
    
    def _ensure_csv_header(self):
        """Ensure CSV file exists with proper header"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'transaction_id', 'timestamp', 'description', 
                    'amount', 'currency', 'transaction_type', 'source'
                ])
                writer.writeheader()
    
    def save_transactions(self, transactions: List[Transaction]) -> None:
        """Append new transactions to CSV file"""
        if not transactions:
            return
            
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'transaction_id', 'timestamp', 'description', 
                'amount', 'currency', 'transaction_type', 'source'
            ])
            for transaction in transactions:
                writer.writerow(transaction.to_dict())
    
    def load_transactions(self) -> List[Transaction]:
        """Load all transactions from CSV file"""
        transactions = []
        
        if not self.csv_file.exists():
            return transactions
            
        with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    transactions.append(Transaction.from_dict(row))
                except (ValueError, KeyError) as e:
                    # Log error but continue processing other rows
                    print(f"Error parsing transaction row {row}: {e}")
                    continue
        
        return transactions
    
    def get_transaction_count(self) -> int:
        """Get total number of transactions"""
        return len(self.load_transactions())
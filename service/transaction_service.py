from typing import List, Union
from storage import Transaction, TransactionStorage
from .wechat_parser import WeChatParser
from .alipay_parser import AlipayParser


class TransactionService:
    """Business logic layer for transaction operations"""
    
    def __init__(self, storage: TransactionStorage = None):
        self.storage = storage or TransactionStorage()
    
    def process_uploaded_file(self, csv_content: str, source_type: str) -> int:
        """
        Process uploaded CSV file and save transactions.
        
        Args:
            csv_content: Raw CSV content as string
            source_type: 'wechat' or 'alipay'
            
        Returns:
            Number of transactions processed
        """
        transactions = []
        
        if source_type.lower() == 'wechat':
            transactions = WeChatParser.parse_csv(csv_content)
        elif source_type.lower() == 'alipay':
            transactions = AlipayParser.parse_csv(csv_content)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        # Save transactions to storage
        self.storage.save_transactions(transactions)
        
        return len(transactions)
    
    def get_all_transactions(self) -> List[Transaction]:
        """Get all transactions from storage"""
        return self.storage.load_transactions()
    
    def get_transactions_by_source(self, source: str) -> List[Transaction]:
        """Get transactions filtered by source (wechat/alipay)"""
        all_transactions = self.storage.load_transactions()
        return [t for t in all_transactions if t.source.lower() == source.lower()]
    
    def get_transaction_summary(self) -> dict:
        """Get summary statistics of all transactions"""
        transactions = self.storage.load_transactions()
        
        if not transactions:
            return {
                'total_count': 0,
                'wechat_count': 0,
                'alipay_count': 0,
                'total_income': 0.0,
                'total_expense': 0.0,
                'net_amount': 0.0
            }
        
        wechat_count = len([t for t in transactions if t.source == 'wechat'])
        alipay_count = len([t for t in transactions if t.source == 'alipay'])
        
        income_transactions = [t for t in transactions if t.transaction_type == 'income']
        expense_transactions = [t for t in transactions if t.transaction_type == 'expense']
        
        total_income = sum(t.amount for t in income_transactions)
        total_expense = sum(t.amount for t in expense_transactions)
        
        return {
            'total_count': len(transactions),
            'wechat_count': wechat_count,
            'alipay_count': alipay_count,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_amount': total_income - total_expense
        }
import csv
import io
from datetime import datetime
from typing import List, Tuple
from storage.models import Transaction
import uuid


class WeChatParser:
    """Parse WeChat transaction CSV format"""
    
    @staticmethod
    def parse_csv(csv_content: str) -> List[Transaction]:
        """
        Parse WeChat CSV format and return list of transactions.
        Assumes common WeChat export format with columns for time, description, amount, etc.
        """
        transactions = []
        
        # Use StringIO to treat string as file-like object
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        for row in reader:
            try:
                # Try to parse common WeChat CSV format
                # Adapt these field names based on actual WeChat export format
                transaction = WeChatParser._parse_row(row)
                if transaction:
                    transactions.append(transaction)
            except Exception as e:
                print(f"Error parsing WeChat row {row}: {e}")
                continue
        
        return transactions
    
    @staticmethod
    def _parse_row(row: dict) -> Transaction:
        """Parse a single WeChat CSV row into Transaction object"""
        # Try different possible column names for WeChat exports
        timestamp_fields = ['时间', 'Time', 'Date', 'Timestamp', 'timestamp']
        desc_fields = ['商品', 'Description', 'Merchant', 'Item', 'description']
        amount_fields = ['金额(元)', 'Amount', 'Money', 'amount']
        type_fields = ['收/支', 'Type', 'Transaction Type', 'type']
        
        # Extract timestamp
        timestamp_str = None
        for field in timestamp_fields:
            if field in row and row[field]:
                timestamp_str = row[field]
                break
        
        if not timestamp_str:
            raise ValueError("No timestamp found")
        
        # Parse timestamp (try different formats)
        timestamp = WeChatParser._parse_timestamp(timestamp_str)
        
        # Extract description
        description = ""
        for field in desc_fields:
            if field in row and row[field]:
                description = row[field]
                break
        
        # Extract amount
        amount_str = ""
        for field in amount_fields:
            if field in row and row[field]:
                amount_str = row[field]
                break
        
        if not amount_str:
            raise ValueError("No amount found")
        
        # Clean and parse amount
        amount = WeChatParser._parse_amount(amount_str)
        
        # Extract transaction type
        transaction_type = "expense"  # default
        for field in type_fields:
            if field in row and row[field]:
                type_val = row[field].lower()
                if '收入' in type_val or 'income' in type_val:
                    transaction_type = "income"
                elif '支出' in type_val or 'expense' in type_val:
                    transaction_type = "expense"
                break
        
        # If no type field found, use amount to determine type
        if not any(field in row for field in type_fields):
            transaction_type = "income" if amount > 0 else "expense"
        
        return Transaction(
            transaction_id=str(uuid.uuid4()),
            timestamp=timestamp,
            description=description or "WeChat Transaction",
            amount=abs(amount),  # Store as positive, use transaction_type for direction
            currency="CNY",  # Default for WeChat
            transaction_type=transaction_type,
            source="wechat"
        )
    
    @staticmethod
    def _parse_timestamp(timestamp_str: str) -> datetime:
        """Parse timestamp from various formats"""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str.strip(), fmt)
            except ValueError:
                continue
        
        # If all else fails, try to parse ISO format
        try:
            return datetime.fromisoformat(timestamp_str.replace('T', ' ').replace('Z', ''))
        except ValueError:
            raise ValueError(f"Could not parse timestamp: {timestamp_str}")
    
    @staticmethod
    def _parse_amount(amount_str: str) -> float:
        """Parse amount from string, handling various formats"""
        # Remove common currency symbols and spaces
        cleaned = amount_str.replace('¥', '').replace('$', '').replace(',', '').replace(' ', '')
        
        # Handle negative amounts
        is_negative = cleaned.startswith('-') or cleaned.startswith('(')
        cleaned = cleaned.replace('-', '').replace('(', '').replace(')', '')
        
        try:
            amount = float(cleaned)
            return -amount if is_negative else amount
        except ValueError:
            raise ValueError(f"Could not parse amount: {amount_str}")
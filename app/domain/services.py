import os
from typing import List
from dotenv import load_dotenv

from app.domain.models import Payment
from app.data.repository import (
    get_all_payments,
    save_payments_to_csv,
    FILE_PATH,
    upsert_payments_to_csv,
)
from app.data.alipay_parser import parse_alipay_file

import csv

load_dotenv()
CATEGORIES_CSV_PATH = os.getenv("CATEGORIES_CSV_PATH", "resources/categories.csv")

class PaymentService:
    def __init__(self):
        self.payments: List[Payment] = get_all_payments()
        self.categories: List[str] = self._load_categories()

    def _load_categories(self) -> List[str]:
        try:
            with open(CATEGORIES_CSV_PATH, "r", encoding="utf-8") as f:
                return sorted({line.strip() for line in f if line.strip()})
        except FileNotFoundError:
            return []

    def _persist_categories(self):
        with open(CATEGORIES_CSV_PATH, "w", encoding="utf-8", newline="") as f:
            for cat in sorted(set(self.categories)):
                f.write(cat + "\n")

    def _persist_payments(self):
        save_payments_to_csv(FILE_PATH, self.payments)

    def list_categories(self) -> List[str]:
        return sorted(set(self.categories))

    def add_category(self, name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("Category name cannot be empty")
        if name in self.categories:
            return name
        self.categories.append(name)
        self._persist_categories()
        return name

    def update_payment_category(self, payment_id: str, cust_category: str) -> None:
        updated = False
        for p in self.payments:
            if p.id == payment_id:
                p.cust_category = cust_category
                updated = True
                break
        if updated:
            self._persist_payments()
        else:
            raise ValueError(f"Payment with id {payment_id} not found")

    def update_merchant_categories(self, payment_id: str, cust_category: str) -> int:
        merchant = None
        for p in self.payments:
            if p.id == payment_id:
                merchant = p.merchant
                break
        if merchant is None:
            raise ValueError(f"Payment with id {payment_id} not found")
        count = 0
        for p in self.payments:
            if p.merchant == merchant:
                p.cust_category = cust_category
                count += 1
        if count > 0:
            self._persist_payments()
        return count

    def import_alipay_payments(self, source_filepath: str) -> int:
        payments = parse_alipay_file(source_filepath)
        added = upsert_payments_to_csv(payments)
        self.payments = get_all_payments()
        return added

    def import_wechat_payments(self, source_filepath: str) -> int:
        from app.data.wechat_parser import parse_wechat_file
        payments = parse_wechat_file(source_filepath)
        added = upsert_payments_to_csv(payments)
        self.payments = get_all_payments()
        return added

    def list_payments(self) -> List[Payment]:
        return self.payments

# Singleton instance for use in API
payment_service = PaymentService()

def list_categories() -> List[str]:
    return payment_service.list_categories()

def add_category(name: str) -> str:
    return payment_service.add_category(name)

def update_payment_category(payment_id: str, cust_category: str) -> None:
    payment_service.update_payment_category(payment_id, cust_category)

def update_merchant_categories(payment_id: str, cust_category: str) -> int:
    return payment_service.update_merchant_categories(payment_id, cust_category)

def import_alipay_payments(source_filepath: str) -> int:
    return payment_service.import_alipay_payments(source_filepath)

def import_wechat_payments(source_filepath: str) -> int:
    return payment_service.import_wechat_payments(source_filepath)

def list_payments() -> List[Payment]:
    return payment_service.list_payments()

if __name__ == '__main__':
    # get file path from options
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m app.data.services <filepathAlipay> <filepathWeChat>")
    else:
        filepathAli = sys.argv[1]
        filepathWe = sys.argv[2]
        import_alipay_payments(filepathAli)
        import_wechat_payments(filepathWe)
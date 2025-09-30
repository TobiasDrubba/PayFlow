import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from app.domain.models import Payment
from app.data.repository import (
    get_all_payments,
    save_payments_to_csv,
    FILE_PATH,
    upsert_payments_to_csv,
    load_category_tree,
    get_all_child_categories,
    save_category_tree,
)
from app.utils.aggregation import sum_payments_by_category, build_sankey_data
from app.data.alipay_parser import parse_alipay_file

import csv

load_dotenv()
CATEGORIES_CSV_PATH = os.getenv("CATEGORIES_CSV_PATH", "resources/categories.csv")

class PaymentService:
    def __init__(self):
        self.payments: List[Payment] = get_all_payments()
        self.category_tree: Dict[str, Any] = load_category_tree()

    def list_categories(self) -> List[str]:
        # Return all child categories only
        return get_all_child_categories(self.category_tree)

    def update_category_tree(self, new_tree: Dict[str, Any]) -> None:
        save_category_tree(new_tree)
        self.category_tree = new_tree

    def _persist_payments(self):
        save_payments_to_csv(FILE_PATH, self.payments)

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

    def import_tsinghua_card_payments(self, source_filepath: str) -> int:
        from app.data.tsinghua_card_parser import parse_tsinghua_card_file
        payments = parse_tsinghua_card_file(source_filepath)
        added = upsert_payments_to_csv(payments)
        self.payments = get_all_payments()
        return added

    def list_payments(self) -> List[Payment]:
        return self.payments

# Singleton instance for use in API
payment_service = PaymentService()

def list_categories() -> List[str]:
    return payment_service.list_categories()

def update_payment_category(payment_id: str, cust_category: str) -> None:
    payment_service.update_payment_category(payment_id, cust_category)

def update_merchant_categories(payment_id: str, cust_category: str) -> int:
    return payment_service.update_merchant_categories(payment_id, cust_category)

def import_alipay_payments(source_filepath: str) -> int:
    return payment_service.import_alipay_payments(source_filepath)

def import_wechat_payments(source_filepath: str) -> int:
    return payment_service.import_wechat_payments(source_filepath)

def import_tsinghua_card_payments(source_filepath: str) -> int:
    return payment_service.import_tsinghua_card_payments(source_filepath)

def get_category_tree():
    return payment_service.category_tree

def update_category_tree(new_tree: Dict[str, Any]) -> None:
    payment_service.update_category_tree(new_tree)

def list_payments() -> List[Payment]:
    return payment_service.list_payments()

def aggregate_payments_by_category(payments: List[Payment], category_tree: dict, start_date=None, end_date=None):
    return sum_payments_by_category(payments, category_tree, start_date, end_date)

def aggregate_payments_sankey(payments: List[Payment], category_tree: dict, start_date=None, end_date=None):
    """
    Aggregates payments and returns Sankey diagram data: nodes and links.
    """
    result = sum_payments_by_category(payments, category_tree, start_date, end_date)
    sankey_data = build_sankey_data(result, category_tree)
    return sankey_data

if __name__ == '__main__':
    # get file path from options
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.data.services <filepathAlipay> <filepathWeChat> <filepathTsinghuaCard>")
    else:
        filepathTsinghua = sys.argv[1]
        import_tsinghua_card_payments(filepathTsinghua)
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
    save_category_tree,
    get_all_child_categories,
    get_category_tree,
    update_category_tree,
)
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

    def add_category(self, parent: str, child: str, subparent: str = None) -> str:
        """
        Add a child category under a parent (and optional subparent).
        Supports:
          - List parents: ["Food", "Drink"] -> append child string
          - Dict-of-nulls parents: {"Taxi": None} -> set key with None
          - Subparent path: parent -> dict -> subparent -> dict-of-nulls -> child: None
        When converting an existing list parent to support subparents, it will be
        transformed into a dict-of-nulls preserving existing leaves.
        """
        tree = self.category_tree
        parent = (parent or "").strip()
        child = (child or "").strip()
        if not parent or not child:
            raise ValueError("Parent and child category names cannot be empty")

        if subparent:
            subparent = subparent.strip()
            if parent not in tree:
                tree[parent] = {}
            # If parent is a list, convert to dict-of-nulls preserving elements
            if isinstance(tree[parent], list):
                existing = tree[parent]
                tree[parent] = {name: None for name in existing if isinstance(name, str)}
            elif not isinstance(tree[parent], dict):
                tree[parent] = {}
            # Ensure subparent exists as dict
            if subparent not in tree[parent] or not isinstance(tree[parent][subparent], dict):
                tree[parent][subparent] = {}
            # Add child as a leaf under subparent (dict-of-nulls)
            tree[parent][subparent][child] = None
        else:
            if parent not in tree:
                # Default to list at top-level if not present
                tree[parent] = []
            if isinstance(tree[parent], list):
                if child not in tree[parent]:
                    tree[parent].append(child)
            elif isinstance(tree[parent], dict):
                # For dict parents, add leaf as key: None
                tree[parent][child] = None
            else:
                # Fallback: coerce to list
                tree[parent] = [child]

        save_category_tree(tree)
        self.category_tree = tree
        return child

    def get_category_tree(self) -> Dict[str, Any]:
        return get_category_tree()

    def update_category_tree(self, new_tree: Dict[str, Any]) -> None:
        update_category_tree(new_tree)
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

    def list_payments(self) -> List[Payment]:
        return self.payments

# Singleton instance for use in API
payment_service = PaymentService()

def list_categories() -> List[str]:
    return payment_service.list_categories()

def add_category(parent: str, child: str, subparent: str = None) -> str:
    return payment_service.add_category(parent, child, subparent)

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
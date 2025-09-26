# app/domain/services.py
from typing import List


from app.domain.models import Payment
from app.data.repository import get_all_payments, save_payments_to_csv, FILE_PATH

from app.data.alipay_parser import parse_alipay_file
from app.data.repository import upsert_payments_to_csv

def list_categories() -> List[str]:
    """
    Returns a sorted list of unique custom categories from all payments.
    """
    payments = get_all_payments()
    cats = set()
    for p in payments:
        if p.cust_category:
            print(p.cust_category)
            cats.add(p.cust_category.strip())
    print(cats)
    return sorted(cats)

def add_category(name: str) -> str:
    """
    Adds a new custom category by creating a dummy payment entry with that category,
    or by updating all payments with the new category if not present.
    """
    name = name.strip()
    if not name:
        raise ValueError("Category name cannot be empty")
    # If already exists, just return
    if name in list_categories():
        return name
    # Add to the first payment with empty cust_category, or create a dummy if needed
    payments = get_all_payments()
    for p in payments:
        if not p.cust_category:
            p.cust_category = name
            save_payments_to_csv(FILE_PATH, payments)
            return name
    # If all payments have a cust_category, just add to the first one (or handle differently)
    if payments:
        payments[0].cust_category = name
        save_payments_to_csv(FILE_PATH, payments)
        return name
    # If no payments exist, do nothing
    return name

def update_payment_category(payment_id: str, cust_category: str) -> None:
    """
    Updates the custom category for a single payment by id.
    """
    payments = get_all_payments()
    updated = False
    for p in payments:
        if p.id == payment_id:
            p.cust_category = cust_category
            updated = True
            break
    if updated:
        save_payments_to_csv(FILE_PATH, payments)
    else:
        raise ValueError(f"Payment with id {payment_id} not found")

def update_merchant_categories(payment_id: str, cust_category: str) -> int:
    """
    Updates the custom category for all payments of the same merchant as the given payment_id.
    Returns the number of updated payments.
    """
    payments = get_all_payments()
    merchant = None
    for p in payments:
        if p.id == payment_id:
            merchant = p.merchant
            break
    if merchant is None:
        raise ValueError(f"Payment with id {payment_id} not found")
    count = 0
    for p in payments:
        if p.merchant == merchant:
            p.cust_category = cust_category
            count += 1
    if count > 0:
        save_payments_to_csv(FILE_PATH, payments)
    return count

def import_alipay_payments(source_filepath: str) -> int:
    """
    Service-layer function:
    - Reads payments from an Alipay export file via parse_alipay_file
    - Stores them to CSV via repository, only adding new payments by id
    Returns the number of newly added payments.
    """
    payments = parse_alipay_file(source_filepath)
    added = upsert_payments_to_csv(payments)
    return added


def import_wechat_payments(source_filepath: str) -> int:
    """
    Service-layer function:
    - Reads payments from a WeChat export file via parse_wechat_file
    - Stores them to CSV via repository, only adding new payments by id
    Returns the number of newly added payments.
    """
    from app.data.wechat_parser import parse_wechat_file  # Import the parser
    payments = parse_wechat_file(source_filepath)
    added = upsert_payments_to_csv(payments)
    return added


def list_payments() -> List[Payment]:
    """
    Service-layer function to fetch all existing payments from storage.
    """
    return get_all_payments()

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
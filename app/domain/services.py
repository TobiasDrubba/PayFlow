from typing import List, Dict, Any

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
from app.utils.sum import sum_payments_in_range
from app.data.alipay_parser import parse_alipay_file
import tempfile
import shutil
from app.domain.models import PaymentSource
from fastapi import UploadFile
import os

class PaymentService:
    def __init__(self):
        self.payments: List[Payment] = get_all_payments()
        self.category_tree: Dict[str, Any] = load_category_tree()
        valid_categories = set(get_all_child_categories(self.category_tree))
        for p in self.payments:
            if p.cust_category not in valid_categories and p.cust_category != "":
                raise ValueError(f"Invalid cust_category '{p.cust_category}' in payment id {p.id}")

    def child_categories(self) -> List[str]:
        # Return all child categories only
        return get_all_child_categories(self.category_tree)

    def update_category_tree(self, new_tree: Dict[str, Any]) -> None:
        # Identify deleted child categories
        old_child_categories = set(get_all_child_categories(self.category_tree))
        new_child_categories = set(get_all_child_categories(new_tree))
        deleted_categories = old_child_categories - new_child_categories

        # Remove deleted categories from payments
        changed = False
        for p in self.payments:
            if p.cust_category in deleted_categories:
                p.cust_category = ""
                changed = True
        if changed:
            self._persist_payments()

        # Now update the tree
        save_category_tree(new_tree)
        self.category_tree = new_tree

    def _persist_payments(self):
        save_payments_to_csv(FILE_PATH, self.payments)

    def _validate_category(self, cust_category: str) -> None:
        # Security: Ensure cust_category is a valid child category
        valid_categories = set(self.child_categories())
        if cust_category not in valid_categories and cust_category != "":
            raise ValueError(f"Invalid child category: {cust_category}")

    def update_payment_category(self, payment_id: str, cust_category: str) -> None:
        self._validate_category(cust_category)
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
        self._validate_category(cust_category)
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

async def import_payment_files_service(files: list, types: list) -> dict:
    """
    Handles importing up to 3 payment files, each with its own type.
    Returns dict with keys: imported (int), errors (list).
    """
    if not files or len(files) > 3:
        return {"imported": 0, "errors": ["Select 1-3 files."]}
    if not types or len(types) != len(files):
        return {"imported": 0, "errors": ["A type must be specified for each file."]}

    import_funcs = {
        PaymentSource.ALIPAY.value: import_alipay_payments,
        PaymentSource.WECHAT.value: import_wechat_payments,
        PaymentSource.TSINGHUA_CARD.value: import_tsinghua_card_payments,
    }

    imported = 0
    errors = []
    for file, type in zip(files, types):
        if type not in import_funcs:
            errors.append(f"{getattr(file, 'filename', str(file))}: Invalid or unsupported payment type.")
            try:
                file.file.close()
            except Exception:
                pass
            continue
        try:
            # Preserve file extension for compatibility with openpyxl and pandas
            filename = getattr(file, "filename", "upload")
            _, ext = os.path.splitext(filename)
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name
            imported += import_funcs[type](tmp_path)
        except Exception as e:
            errors.append(f"{getattr(file, 'filename', str(file))}: {str(e)}")
        finally:
            try:
                file.file.close()
            except Exception:
                pass

    return {"imported": imported, "errors": errors}

def get_sums_for_ranges_service(ranges: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    payments = list_payments()
    result = {}
    for name, range_dict in ranges.items():
        start = range_dict.get("start")
        end = range_dict.get("end")
        result[name] = sum_payments_in_range(payments, start, end)
    return result

# Singleton instance for use in API
payment_service = PaymentService()

def list_categories() -> List[str]:
    return payment_service.child_categories()

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
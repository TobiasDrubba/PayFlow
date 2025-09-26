# app/domain/services.py
from typing import List


from app.domain.models import Payment
from app.data.repository import get_all_payments


from app.data.alipay_parser import parse_alipay_file
from app.data.repository import upsert_payments_to_csv


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
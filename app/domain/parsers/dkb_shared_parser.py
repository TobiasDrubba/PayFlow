from typing import List

from app.domain.models.payment import Payment, PaymentSource
from app.domain.parsers.dkb_parser import parse_dkb_file


def parse_dkb_shared_file(filepath: str) -> List[Payment]:
    """
    Parse a DKB CSV export for a shared account: same format as DKB, amounts halved.
    """
    payments = parse_dkb_file(filepath)
    for payment in payments:
        payment.amount /= 2
        payment.source = PaymentSource.DKB_SHARED
    return payments


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.domain.parsers.dkb_shared_parser <filepath>")
    else:
        filepath = sys.argv[1]
        parsed = parse_dkb_shared_file(filepath)
        for p in parsed:
            print(p)

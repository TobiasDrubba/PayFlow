from typing import List

from app.domain.models.payment import Payment, PaymentSource, PaymentType

# Trigger words for drink auto-categorization (mix of English and Chinese names)
DRINK_TRIGGER_WORDS = {
    "coco",
    "coffee",
    "咖啡",
    "luckin",
    "瑞幸",
    "starbucks",
    "星巴克",
    "heytea",
    "喜茶",
    "naixue",
    "奈雪",
    "奈雪的茶",
    "蜜雪冰城",
    "milk tea",
    "奶茶",
    "tea",
    "茶",
    "costa",
    "coff",
    "bubble tea",
    "珍珠奶茶",
}


def auto_categorize_drinks(payments: List[Payment]) -> None:
    """
    Mutate payments in-place: for expense payments without an explicit category,
    if merchant or note contains any trigger word, set payment.category = 'Drink'.
    """
    trigger_lowers = {t.lower() for t in DRINK_TRIGGER_WORDS}
    allowed_sources = {PaymentSource.ALIPAY, PaymentSource.WECHAT}
    for p in payments:
        # Only process payments from the allowed parsers
        if getattr(p, "source", None) not in allowed_sources:
            continue
        # Only tag expenses and only if no explicit category already set
        if getattr(p, "type", None) == PaymentType.EXPENSE and not getattr(
            p, "category", ""
        ):
            merchant = (p.merchant or "").lower()
            note = (p.note or "").lower()
            combined = f"{merchant} {note}"
            for trig in trigger_lowers:
                if trig in combined:
                    p.category = "Drink"
                    break


def auto_categorize_tsinghua_water(payments: List[Payment]) -> None:
    for p in payments:
        # Only process TSINGHUA_CARD payments
        if getattr(p, "source", None) != PaymentSource.TSINGHUA_CARD:
            continue
        # Only tag expenses and only if no explicit category already set
        if getattr(p, "type", None) == PaymentType.EXPENSE:
            try:
                amt = abs(float(p.amount))
            except Exception:
                continue
            merchant = (p.merchant or "").lower()
            if amt < 1.0 and "bot" in merchant:
                p.category = "Water"

import asyncio

from dotenv import load_dotenv
from googletrans import Translator
from sqlalchemy.orm import Session

# Simple translation using HuggingFace pipeline
from transformers import pipeline

from app.data.repositories.payment_repository import (
    get_all_child_categories,
    get_all_payments,
    get_category_tree,
)
from app.domain.models.payment import Payment

translator = Translator()
load_dotenv()
CATEGORIES_CSV_PATH = "resources/categories.csv"


def load_categories(csv_path: str):
    with open(csv_path, "r", encoding="utf-8") as f:
        return sorted({line.strip() for line in f if line.strip()})


async def translate_text(text: str) -> str:
    result = await translator.translate(text, src="zh-cn", dest="en")
    return result.text


async def classify_payments(payments: list[Payment]):
    categories = load_categories(CATEGORIES_CSV_PATH)
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    for p in payments:
        if not p.category:
            t_m = await translate_text(p.merchant)
            t_n = await translate_text(p.note)
            input_text = f"{t_m} {t_n}"
            result = classifier(input_text, candidate_labels=categories)
            top_label = result["labels"][0]
            top_score = result["scores"][0]
            if top_score > 0.4:
                p.category = top_label
                print(
                    f"1     Payment {t_m}-{t_n}: classified as "
                    f"'{top_label}' ({round(top_score * 100)}%)"
                )
            else:
                print(
                    f"Payment {t_m}-{t_n}: no confident category found "
                    f"(top: {top_label}, {round(top_score * 100)}%)"
                )
    return payments


async def classify_payments_from_db(db: Session, user_id: int):
    """
    Reads payments from the database and prints the
    most likely category for each payment (if top score > 0).
    Gets categories from the database.
    Tracks classification accuracy for confident predictions (top_score > 0.4).
    Prints accuracy every 10 confident classifications.
    """
    payments, _ = get_all_payments(db, user_id, None, 1, 200)
    category_tree = get_category_tree(db, user_id)
    categories = get_all_child_categories(category_tree)
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    correct = 0
    misclassified = 0
    total_classified = 0
    not_classified = 0
    not_classified_string = ""

    for p in payments:
        if p.category not in [
            "Canteen Breakfast",
            "Canteen Lunch",
            "Canteen Dinner",
            "Card Recharge",
            "",
        ]:
            t_m = await translate_text(p.merchant)
            t_n = await translate_text(p.note)
            input_text = f"{t_m} {t_n}"
            result = classifier(input_text, candidate_labels=categories)
            top_label = result["labels"][0]
            top_score = result["scores"][0]
            if p.category != "" and top_score >= 0.3:
                total_classified += 1
                if top_label == p.category:
                    correct += 1
                    print(
                        f"Payment {t_m}-{t_n}: CORRECT '{top_label}' "
                        f"({round(top_score * 100)}%)"
                    )
                else:
                    misclassified += 1
                    print(
                        f"Payment {t_m}-{t_n}: MISCLASSIFIED actual: '{p.category}', "
                        f"predicted: '{top_label}' ({round(top_score * 100)}%)"
                    )
                # Print accuracy every 10 classified payments
                if total_classified % 10 == 0:
                    accuracy = correct / total_classified * 100
                    print(
                        f"\nClassification accuracy so far: {accuracy:.2f}% "
                        f"({correct}/{total_classified} correct, "
                        f"{misclassified} misclassified)\n"
                    )
            else:
                not_classified += 1
                not_classified_string += (
                    f"Payment {t_m}-{t_n}: most likely class is "
                    f"'{top_label}' ({round(top_score * 100)}%), "
                    f"actual: '{p.category}' (low confidence)\n"
                )

    print(not_classified_string)
    if total_classified > 0:
        accuracy = correct / total_classified * 100
        print(
            f"\nFinal classification accuracy: {accuracy:.2f}% "
            f"({correct}/{total_classified} correct, {misclassified} misclassified)"
        )
    else:
        print("\nNo confident classifications (top_score > 40%) found.")

    print(
        f"Not classified {not_classified} payments: "
        f"{not_classified / len(payments) * 100:.2f}%"
    )


if __name__ == "__main__":
    import argparse

    from sqlalchemy.orm import sessionmaker

    from app.data.base import engine

    parser = argparse.ArgumentParser(description="Classify payments from DB")
    parser.add_argument("--user_id", type=int, required=True, help="User ID")
    args = parser.parse_args()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    asyncio.run(classify_payments_from_db(db, args.user_id))
    db.close()

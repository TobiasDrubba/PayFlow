import asyncio
import time

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

translator = Translator()
load_dotenv()
CATEGORIES_CSV_PATH = "resources/categories.csv"


def load_categories(csv_path: str):
    with open(csv_path, "r", encoding="utf-8") as f:
        return sorted({line.strip() for line in f if line.strip()})


async def translate_text(text: str) -> str:
    result = await translator.translate(text, src="zh-cn", dest="en")
    return result.text


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

    # Start all translation tasks up front
    translation_tasks = {
        p.id: asyncio.create_task(translate_text(p.merchant + " " + p.note))
        for p in payments
        if p.category
        not in [
            "Canteen Breakfast",
            "Canteen Lunch",
            "Canteen Dinner",
            "Card Recharge",
            "",
        ]
    }

    pending_payments = [p for p in payments if p.id in translation_tasks]
    classified_ids = set()
    while pending_payments:
        for p in list(pending_payments):
            task = translation_tasks[p.id]
            if task.done():
                t_start_class = time.perf_counter()
                translated = await task
                result = classifier(translated, candidate_labels=categories)
                t_end_class = time.perf_counter()
                print(f"Classification time: {t_end_class - t_start_class:.3f}s")
                top_label = result["labels"][0]
                top_score = result["scores"][0]
                if p.category != "" and top_score >= 0.3:
                    total_classified += 1
                    if top_label == p.category:
                        correct += 1
                        print(
                            f"Payment {translated}: CORRECT '{top_label}' "
                            f"({round(top_score * 100)}%)"
                        )
                    else:
                        misclassified += 1
                        print(
                            f"Payment {translated}: MISCLASSIFIED actual: "
                            f"'{p.category}', "
                            f"predicted: '{top_label}' ({round(top_score * 100)}%)"
                        )
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
                        f"Payment {translated}: most likely class is "
                        f"'{top_label}' ({round(top_score * 100)}%), "
                        f"actual: '{p.category}' (low confidence)\n"
                    )
                classified_ids.add(p.id)
                pending_payments.remove(p)
        await asyncio.sleep(0.05)

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

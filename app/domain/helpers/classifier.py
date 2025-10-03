import os

from dotenv import load_dotenv

# Simple translation using HuggingFace pipeline
from transformers import pipeline
from transformers import pipeline as hf_pipeline

from app.domain.models.payment import Payment

translator = hf_pipeline("translation", model="tryHelsinki-NLP/opus-mt-zh-en")

load_dotenv()
CATEGORIES_CSV_PATH = os.getenv("CATEGORIES_CSV_PATH", "resources/categories.csv")


def load_categories(csv_path: str):
    with open(csv_path, "r", encoding="utf-8") as f:
        return sorted({line.strip() for line in f if line.strip()})


def translate_text(text: str) -> str:
    if not text.strip():
        return ""
    # Only translate if contains Chinese characters
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return translator(text, max_length=128)[0]["translation_text"]
    return text


def classify_payments(payments: list[Payment]):
    categories = load_categories(CATEGORIES_CSV_PATH)
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    for p in payments:
        if not p.category:
            t_m = translate_text(p.merchant)
            t_n = translate_text(p.note)
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

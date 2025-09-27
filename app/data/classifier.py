import os
from transformers import pipeline
from app.data.repository import get_all_payments, save_payments_to_csv, FILE_PATH
from app.domain.models import Payment
from dotenv import load_dotenv
import csv

# Simple translation using HuggingFace pipeline (can be replaced with more robust solution)
from transformers import pipeline as hf_pipeline
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
    if any('\u4e00' <= ch <= '\u9fff' for ch in text):
        return translator(text, max_length=128)[0]['translation_text']
    return text

def classify_payments():
    payments = get_all_payments()
    categories = load_categories(CATEGORIES_CSV_PATH)
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

    updated = False
    for p in payments:
        if not p.cust_category:
            t_m = translate_text(p.merchant)
            t_n = translate_text(p.note)
            input_text = f"{t_m} {t_n}"
            result = classifier(input_text, candidate_labels=categories)
            top_label = result['labels'][0]
            top_score = result['scores'][0]
            if top_score > 0.4:
                p.cust_category = top_label
                updated = True
                print(f"1     Payment {t_m}-{t_n}: classified as '{top_label}' ({round(top_score * 100)}%)")
            else:
                print(f"Payment {t_m}-{t_n}: no confident category found (top: {top_label}, {round(top_score * 100)}%)")
    if updated:
        save_payments_to_csv(FILE_PATH, payments)
        print("Updated payments with classified categories.")
    else:
        print("No payments updated.")

if __name__ == "__main__":
    classify_payments()

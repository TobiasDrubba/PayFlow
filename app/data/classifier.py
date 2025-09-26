from transformers import pipeline

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
labels = ["household", "taxi", "bike", "restaurant", "drink"]

while True:
    text = input("Enter text to classify (or 'e' to exit): ")
    if text.strip().lower() == 'e':
        break
    result = classifier(text, candidate_labels=labels)
    top_labels = result['labels'][:2]
    top_scores = result['scores'][:2]
    for label, score in zip(top_labels, top_scores):
        print(f"{label} ({round(score * 100)}%)")

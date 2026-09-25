import json
from pathlib import Path

from frontdoor.engine import digest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
train = json.loads((ROOT / "data/sms-train.json").read_text())
vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=20000, sublinear_tf=True)
matrix = vectorizer.fit_transform([r["message"]["body"] for r in train])
classifier = LogisticRegression(C=4, class_weight="balanced", random_state=42, max_iter=500)
classifier.fit(matrix, [r["expected"] for r in train])
model = {
    "train_hash": digest(train),
    "vocabulary": {word: int(index) for word, index in vectorizer.vocabulary_.items()},
    "idf": vectorizer.idf_.tolist(),
    "coefficient": classifier.coef_[0].tolist(),
    "intercept": float(classifier.intercept_[0]),
    "scope": "Binary spam only; trained on the UCI SMS training partition.",
}
output = ROOT / "models/spam-linear.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(model) + "\n")
print(f"Saved portable baseline with {len(model['vocabulary'])} features")

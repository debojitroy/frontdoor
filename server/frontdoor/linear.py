"""Portable inference for the bundled, locally trained TF-IDF/logistic baseline."""

import math
import re
from collections import Counter
from itertools import pairwise


def predict_linear(text, model):
    words = re.findall(r"(?u)\b\w\w+\b", text.lower())
    terms = words + [" ".join(pair) for pair in pairwise(words)]
    counts = Counter(terms)
    values = {
        index: (1 + math.log(counts[term])) * model["idf"][index]
        for term, index in model["vocabulary"].items()
        if term in counts
    }
    norm = math.sqrt(sum(value * value for value in values.values())) or 1
    score = model["intercept"] + sum(
        model["coefficient"][index] * value / norm for index, value in values.items()
    )
    probability = 1 / (1 + math.exp(-max(-700, min(700, score))))
    return {"spam": probability >= 0.5, "probability": probability}

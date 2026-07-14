"""Agreement metrics for judge calibration (Design.md §6, dependency-free).

Levels are ordinal (L1–L5), so we report both Cohen's κ (nominal) and the
quadratic-weighted κ (which credits near-misses — an L4 scored L3 hurts less
than an L4 scored L1). Also exact accuracy, within-one agreement, and mean
absolute error. All functions operate over a fixed category space so the
weighting is stable even when some levels are absent from the sample.
"""

from __future__ import annotations

LEVELS = [1, 2, 3, 4, 5]


def confusion_matrix(labels: list[int], preds: list[int], categories: list[int] = LEVELS):
    idx = {c: i for i, c in enumerate(categories)}
    m = [[0] * len(categories) for _ in categories]
    for t, p in zip(labels, preds):
        m[idx[t]][idx[p]] += 1
    return m


def accuracy(labels: list[int], preds: list[int]) -> float:
    if not labels:
        return 0.0
    return sum(1 for t, p in zip(labels, preds) if t == p) / len(labels)


def within_one(labels: list[int], preds: list[int]) -> float:
    if not labels:
        return 0.0
    return sum(1 for t, p in zip(labels, preds) if abs(t - p) <= 1) / len(labels)


def mae(labels: list[int], preds: list[int]) -> float:
    if not labels:
        return 0.0
    return sum(abs(t - p) for t, p in zip(labels, preds)) / len(labels)


def cohen_kappa(labels: list[int], preds: list[int], categories: list[int] = LEVELS) -> float:
    n = len(labels)
    if n == 0:
        return 0.0
    k = len(categories)
    m = confusion_matrix(labels, preds, categories)
    po = sum(m[i][i] for i in range(k)) / n
    row = [sum(m[i]) for i in range(k)]
    col = [sum(m[i][j] for i in range(k)) for j in range(k)]
    pe = sum((row[i] / n) * (col[i] / n) for i in range(k))
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else 0.0
    return (po - pe) / (1 - pe)


def quadratic_weighted_kappa(
    labels: list[int], preds: list[int], categories: list[int] = LEVELS
) -> float:
    n = len(labels)
    if n == 0:
        return 0.0
    k = len(categories)
    obs = confusion_matrix(labels, preds, categories)
    row = [sum(obs[i]) for i in range(k)]
    col = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    denom = (k - 1) ** 2
    num = 0.0
    den = 0.0
    for i in range(k):
        for j in range(k):
            w = ((i - j) ** 2) / denom
            e = row[i] * col[j] / n
            num += w * obs[i][j]
            den += w * e
    if den == 0:
        return 1.0
    return 1 - num / den


def interpret_kappa(k: float) -> str:
    """Landis & Koch bands."""
    if k < 0:
        return "poor (worse than chance)"
    if k < 0.20:
        return "slight"
    if k < 0.40:
        return "fair"
    if k < 0.60:
        return "moderate"
    if k < 0.80:
        return "substantial"
    return "almost perfect"

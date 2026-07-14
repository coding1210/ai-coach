from app.eval.metrics import (
    accuracy,
    cohen_kappa,
    mae,
    quadratic_weighted_kappa,
    within_one,
)


def test_perfect_agreement():
    labels = [1, 2, 3, 4, 5]
    preds = [1, 2, 3, 4, 5]
    assert accuracy(labels, preds) == 1.0
    assert cohen_kappa(labels, preds) == 1.0
    assert quadratic_weighted_kappa(labels, preds) == 1.0
    assert mae(labels, preds) == 0.0
    assert within_one(labels, preds) == 1.0


def test_chance_level_kappa_is_zero():
    # 2x2 checkerboard: observed agreement == expected → κ = 0.
    labels = [1, 1, 2, 2]
    preds = [1, 2, 1, 2]
    assert cohen_kappa(labels, preds, categories=[1, 2]) == 0.0
    assert quadratic_weighted_kappa(labels, preds, categories=[1, 2]) == 0.0


def test_near_miss_credited_by_weighted_kappa():
    # Every prediction off by one in the same direction.
    labels = [1, 2, 3, 4]
    preds = [2, 3, 4, 5]
    assert accuracy(labels, preds) == 0.0
    assert within_one(labels, preds) == 1.0
    assert mae(labels, preds) == 1.0
    # Weighted κ rewards near-misses more than nominal κ.
    assert quadratic_weighted_kappa(labels, preds) > cohen_kappa(labels, preds)


def test_degenerate_constant_predictor():
    # A judge that always says L3 (like the FakeProvider) can't agree by design.
    labels = [1, 2, 4, 5]
    preds = [3, 3, 3, 3]
    assert accuracy(labels, preds) == 0.0
    assert cohen_kappa(labels, preds) == 0.0


def test_within_one_and_mae():
    labels = [1, 3]
    preds = [2, 3]
    assert accuracy(labels, preds) == 0.5
    assert within_one(labels, preds) == 1.0
    assert mae(labels, preds) == 0.5

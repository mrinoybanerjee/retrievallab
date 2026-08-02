import pytest
from retrievallab.evaluation import aggregate, ndcg_at_k, reciprocal_rank


def test_reciprocal_rank_rewards_early_relevance() -> None:
    assert reciprocal_rank([4, 2, 8], {2}) == pytest.approx(0.5)
    assert reciprocal_rank([4, 8], {2}) == 0.0


def test_ndcg_is_normalized() -> None:
    assert ndcg_at_k([2, 4, 9], {2, 4}, k=3) == pytest.approx(1.0)
    assert 0 < ndcg_at_k([9, 4, 2], {2, 4}, k=3) < 1


def test_aggregate_returns_all_public_metrics() -> None:
    report = aggregate(
        [
            {"hit_at_5": 1.0, "reciprocal_rank": 1.0, "ndcg_at_10": 0.9, "abstention_correct": 1.0},
            {"hit_at_5": 0.0, "reciprocal_rank": 0.0, "ndcg_at_10": 0.0, "abstention_correct": 1.0},
        ]
    )
    assert report == {
        "hit_rate_at_5": 0.5,
        "mrr": 0.5,
        "ndcg_at_10": 0.45,
        "abstention_accuracy": 1.0,
    }

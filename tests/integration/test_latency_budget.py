from research.evaluation.latency import (
    POLICY_MAX_BUDGET_SECONDS,
    POLICY_P95_BUDGET_SECONDS,
    benchmark_policy_paths,
)
from research.evaluation.representative_states import representative_policy_games


def test_every_production_incumbent_path_meets_turn_budget() -> None:
    results = benchmark_policy_paths(representative_policy_games(), iterations=25)
    assert results
    assert all(result.p95_seconds <= POLICY_P95_BUDGET_SECONDS for result in results)
    assert all(result.max_seconds <= POLICY_MAX_BUDGET_SECONDS for result in results)
    assert all(result.within_budget for result in results)

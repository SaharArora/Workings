from __future__ import annotations

import pytest

from policies.negotiation.risk_sensitive_pooled import (
    BAD_OUTCOME_Y_THRESHOLD,
    CONTINUATION_MATERIALIZATION_SHRINK,
    RiskParameters,
    apply_agreement_dominance,
    cvar_upper_loss_tail,
    payoff_distribution,
    risk_parameter_grid,
    score_candidate,
    select_risk_candidate,
)


def parameters(*, risk_lambda: float = 0.25) -> RiskParameters:
    return RiskParameters(risk_lambda=risk_lambda, cvar_alpha=0.80, epsilon=0.10)


def test_payoff_distribution_has_explicit_three_branches() -> None:
    branches = payoff_distribution(
        own_value=100,
        q_accept=0.40,
        acceptance_payoff=50,
        continuation_target_payoff=25,
        q_next_opportunity_accept=0.50,
        terminal=False,
    )
    by_name = {branch.name: branch for branch in branches}
    assert by_name["ACCEPT"].probability == pytest.approx(0.40)
    assert by_name["NONACCEPT_CONTINUE"].probability == pytest.approx(
        0.60 * CONTINUATION_MATERIALIZATION_SHRINK * 0.50
    )
    assert sum(branch.probability for branch in branches) == pytest.approx(1)
    assert by_name["TERMINAL_NONAGREEMENT"].raw_payoff == 0
    assert by_name["TERMINAL_NONAGREEMENT"].normalized_payoff == 0.5


def test_terminal_distribution_has_no_continuation_branch() -> None:
    branches = payoff_distribution(
        own_value=100,
        q_accept=0.40,
        acceptance_payoff=50,
        continuation_target_payoff=25,
        q_next_opportunity_accept=1,
        terminal=True,
    )
    assert {branch.name for branch in branches} == {
        "ACCEPT",
        "TERMINAL_NONAGREEMENT",
    }


def test_cvar_uses_worst_upper_loss_tail_with_fractional_atom() -> None:
    # Worst 20% = all of loss 2 (10%) plus half of loss 1 (10%).
    assert cvar_upper_loss_tail(((2, 0.1), (1, 0.2), (-1, 0.7)), alpha=0.8) == pytest.approx(1.5)


def test_loss_convention_is_negative_normalized_payoff() -> None:
    safe = cvar_upper_loss_tail(((-0.75, 1.0),), alpha=0.9)
    bad = cvar_upper_loss_tail(((-0.40, 1.0),), alpha=0.9)
    assert safe == pytest.approx(-0.75)
    assert bad == pytest.approx(-0.40)
    assert 0.75 - 0.25 * safe > 0.40 - 0.25 * bad


def test_chance_and_zero_constraints_are_separate() -> None:
    candidate = score_candidate(
        price=150,
        source=("ROBUST",),
        own_value=100,
        q_accept=0.40,
        acceptance_payoff=50,
        continuation_target=150,
        continuation_target_payoff=50,
        q_next_opportunity_accept=0.50,
        terminal=False,
        parameters=parameters(),
    )
    assert candidate.chance_bad_outcome == 0
    assert candidate.chance_constraint_satisfied
    assert candidate.terminal_zero_probability > 0.50
    assert not candidate.zero_constraint_satisfied
    assert BAD_OUTCOME_Y_THRESHOLD == 0.50


def test_agreement_dominance_removes_near_value_long_shot() -> None:
    long_shot = score_candidate(
        price=200,
        source=("GRID",),
        own_value=100,
        q_accept=0.45,
        acceptance_payoff=100,
        continuation_target=150,
        continuation_target_payoff=50,
        q_next_opportunity_accept=1,
        terminal=False,
        parameters=parameters(risk_lambda=0),
    )
    agreement = score_candidate(
        price=150,
        source=("ROBUST",),
        own_value=100,
        q_accept=0.60,
        acceptance_payoff=50,
        continuation_target=150,
        continuation_target_payoff=50,
        q_next_opportunity_accept=1,
        terminal=False,
        parameters=parameters(risk_lambda=0),
    )
    # Force the intended near-value condition without changing the probabilities.
    from dataclasses import replace

    agreement = replace(
        agreement,
        risk_adjusted_value=long_shot.risk_adjusted_value - 0.005,
        zero_constraint_satisfied=True,
    )
    long_shot = replace(long_shot, zero_constraint_satisfied=True)
    result = apply_agreement_dominance((long_shot, agreement))
    assert result[0].dominated_for_agreement
    assert select_risk_candidate(result, role="seller") == result[1]


def test_locked_grid_has_exactly_36_combinations() -> None:
    grid = risk_parameter_grid()
    assert len(grid) == 36
    assert {(item.risk_lambda, item.cvar_alpha, item.epsilon) for item in grid} == {
        (risk_lambda, alpha, epsilon)
        for risk_lambda in (0.0, 0.10, 0.25, 0.50)
        for alpha in (0.80, 0.90, 0.95)
        for epsilon in (0.10, 0.20, 0.30)
    }

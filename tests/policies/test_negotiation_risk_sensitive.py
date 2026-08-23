from __future__ import annotations

import pytest

from policies.negotiation.risk_sensitive_pooled import (
    bounded_score_loss,
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


@pytest.mark.parametrize("payoff, expected", ((1.0, 0.0), (0.5, 0.5), (0.0, 1.0)))
def test_bounded_score_loss_is_one_minus_payoff(payoff: float, expected: float) -> None:
    assert bounded_score_loss(payoff) == expected


def test_cvar_is_nonnegative_for_valid_bounded_payoff_distribution() -> None:
    losses = tuple(
        (bounded_score_loss(payoff), probability)
        for payoff, probability in ((1.0, 0.2), (0.5, 0.3), (0.0, 0.5))
    )
    for alpha in (0.8, 0.9, 0.95):
        assert cvar_upper_loss_tail(losses, alpha=alpha) >= 0


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
    assert candidate.chance_bad_outcome == candidate.terminal_zero_probability
    assert not candidate.chance_constraint_satisfied
    assert candidate.terminal_zero_probability > 0.50
    assert not candidate.zero_constraint_satisfied


def test_increasing_lambda_cannot_raise_fixed_candidate_score() -> None:
    arguments = dict(
        price=150,
        source=("ROBUST",),
        own_value=100,
        q_accept=0.8,
        acceptance_payoff=50,
        continuation_target=150,
        continuation_target_payoff=50,
        q_next_opportunity_accept=1.0,
        terminal=False,
    )
    unpenalized = score_candidate(**arguments, parameters=parameters(risk_lambda=0.0))
    penalized = score_candidate(**arguments, parameters=parameters(risk_lambda=0.5))
    assert penalized.cvar_loss >= 0
    assert penalized.risk_adjusted_value <= unpenalized.risk_adjusted_value


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
        chance_constraint_satisfied=True,
        zero_constraint_satisfied=True,
    )
    long_shot = replace(
        long_shot,
        chance_constraint_satisfied=True,
        zero_constraint_satisfied=True,
    )
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

import pytest

from theory.bargaining.baselines import (
    bayes_adaptive_reference,
    finite_horizon_offer_alice_share,
    finite_horizon_alice_share,
    finite_horizon_shares,
    rubinstein_alice_share,
    rubinstein_proposer_share,
)


def test_finite_horizon_hand_computed_t_1_2_3() -> None:
    alice, bob = finite_horizon_shares(0.9, 0.8, 3)
    assert alice == pytest.approx((1.0, 0.2, 0.92))
    assert bob == pytest.approx((1.0, 0.1, 0.82))


def test_finite_converges_to_rubinstein() -> None:
    exact = rubinstein_alice_share(0.9, 0.8)
    assert abs(finite_horizon_alice_share(0.9, 0.8, 200) - exact) < 1e-12


def test_bayes_approximation_integrates_full_prior() -> None:
    expected = 0.25 * rubinstein_alice_share(0.9, 0.5) + 0.75 * rubinstein_alice_share(0.9, 0.8)
    assert bayes_adaptive_reference(0.9, {0.5: 0.25, 0.8: 0.75}, finite_rounds=None) == expected


def test_current_proposer_and_remaining_rounds_are_respected() -> None:
    assert finite_horizon_offer_alice_share(
        0.9, 0.8, 2, proposer_is_alice=True
    ) == pytest.approx(0.2)
    assert finite_horizon_offer_alice_share(
        0.9, 0.8, 2, proposer_is_alice=False
    ) == pytest.approx(0.9)


def test_undiscounted_unlimited_operational_convention_is_symmetric() -> None:
    assert rubinstein_alice_share(1, 1) == 0.5
    assert rubinstein_proposer_share(1, 1) == 0.5


def test_bob_bayes_reference_is_bob_proposer_share() -> None:
    expected = 0.25 * rubinstein_proposer_share(0.8, 0.5) + 0.75 * rubinstein_proposer_share(0.8, 0.9)
    assert bayes_adaptive_reference(
        0.8, {0.5: 0.25, 0.9: 0.75}, finite_rounds=None, agent_is_alice=False
    ) == pytest.approx(expected)

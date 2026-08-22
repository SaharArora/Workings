"""Locked bargaining baselines from BUILD_SPEC §4.1."""

from __future__ import annotations

from collections.abc import Mapping


def rubinstein_alice_share(delta_alice: float, delta_bob: float) -> float:
    if not (0 <= delta_alice <= 1 and 0 <= delta_bob <= 1):
        raise ValueError("discount factors must lie in [0, 1]")
    if delta_alice == delta_bob == 1:
        # The undiscounted infinite game has a continuum of stationary splits.
        # Equal split is the explicit symmetric operational convention.
        return 0.5
    return (1 - delta_bob) / (1 - delta_alice * delta_bob)


def rubinstein_proposer_share(own_discount: float, responder_discount: float) -> float:
    """Return the stationary share retained by the player proposing now."""
    return rubinstein_alice_share(own_discount, responder_discount)


def finite_horizon_shares(
    delta_alice: float, delta_bob: float, rounds: int
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return explicit A-proposer and B-proposer own-share sequences for r=1..T."""
    if rounds < 1:
        raise ValueError("rounds must be positive")
    alice = [1.0]
    bob = [1.0]
    for _ in range(2, rounds + 1):
        alice.append(1 - delta_bob * bob[-1])
        bob.append(1 - delta_alice * alice[-2])
    return tuple(alice), tuple(bob)


def finite_horizon_alice_share(delta_alice: float, delta_bob: float, rounds: int) -> float:
    return finite_horizon_shares(delta_alice, delta_bob, rounds)[0][-1]


def finite_horizon_offer_alice_share(
    delta_alice: float,
    delta_bob: float,
    rounds_remaining: int,
    *,
    proposer_is_alice: bool,
) -> float:
    """Return Alice's allocation for the current proposer and remaining horizon."""
    alice_proposer, bob_proposer = finite_horizon_shares(
        delta_alice, delta_bob, rounds_remaining
    )
    if proposer_is_alice:
        return alice_proposer[-1]
    return 1 - bob_proposer[-1]


def bayes_adaptive_reference(
    own_discount: float,
    opponent_prior: Mapping[float, float],
    *,
    finite_rounds: int | None,
    agent_is_alice: bool = True,
) -> float:
    """Bayes-adaptive approximation integrating type-conditioned baseline shares.

    This is explicitly an approximation, not an exact perfect Bayesian equilibrium.
    """
    total = sum(opponent_prior.values())
    if total <= 0:
        raise ValueError("prior must have positive mass")
    result = 0.0
    for opponent_discount, mass in opponent_prior.items():
        if finite_rounds is None:
            own_share = rubinstein_proposer_share(own_discount, opponent_discount)
        else:
            alice_proposer, bob_proposer = finite_horizon_shares(
                own_discount if agent_is_alice else opponent_discount,
                opponent_discount if agent_is_alice else own_discount,
                finite_rounds,
            )
            own_share = alice_proposer[-1] if agent_is_alice else bob_proposer[-1]
        result += mass / total * own_share
    return result

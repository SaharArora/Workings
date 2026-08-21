"""Static-grid v1 minimax-regret fallback; no learned or adaptive component."""

from __future__ import annotations

from collections.abc import Sequence

ROBUST_GRID_POINTS = 5


def evenly_spaced_grid(minimum: float, maximum: float, points: int = ROBUST_GRID_POINTS) -> tuple[float, ...]:
    if points < 2 or maximum <= minimum:
        raise ValueError("a nondegenerate grid needs at least two points")
    step = (maximum - minimum) / (points - 1)
    return tuple(minimum + index * step for index in range(points))


def minimax_regret_price(
    *,
    role: str,
    own_value: float,
    legal_prices: Sequence[float],
    opponent_values: Sequence[float],
) -> float:
    """Select price minimizing maximum regret across the fixed ambiguity grid."""
    if role not in {"seller", "buyer"} or not legal_prices or not opponent_values:
        raise ValueError("invalid robust-policy inputs")

    def payoff(price: float, opponent_value: float) -> float:
        if role == "seller":
            return max(price - own_value, 0.0) if price <= opponent_value else 0.0
        return max(own_value - price, 0.0) if price >= opponent_value else 0.0

    best = {value: max(payoff(price, value) for price in legal_prices) for value in opponent_values}
    def maximum_regret(price: float) -> float:
        return max(best[value] - payoff(price, value) for value in opponent_values)
    return min(legal_prices, key=lambda price: (maximum_regret(price), price if role == "seller" else -price))

"""Pure fixed-mixture anytime-valid betting process from BUILD_SPEC §6.2.

For honest independent 50/50 assignment, X_t = Z_t Y_t has conditional mean one half
the candidate-minus-incumbent mean difference, hence nonpositive under H0. Since X is in
[-1, 1] and every fixed lambda is below one, each multiplier is nonnegative; the convex
mixture remains a valid e-process.
"""

from __future__ import annotations

from dataclasses import dataclass, field

BETTING_FRACTIONS = (0.1, 0.25, 0.5, 0.75)


@dataclass(slots=True)
class BettingProcess:
    components: dict[float, float] = field(
        default_factory=lambda: {value: 1.0 for value in BETTING_FRACTIONS}
    )

    @property
    def value(self) -> float:
        return sum(self.components.values()) / len(self.components)

    def update(self, x: float) -> float:
        if not -1 <= x <= 1:
            raise ValueError("x must lie in [-1, 1]")
        for betting_fraction in BETTING_FRACTIONS:
            self.components[betting_fraction] *= 1 + betting_fraction * x
        return self.value

    def copy_components(self) -> dict[str, float]:
        return {str(value): wealth for value, wealth in self.components.items()}

from __future__ import annotations

import pytest

from glee.payoffs import RawPayoffCategory, bad_outcome


@pytest.mark.parametrize("family", ("negotiation", "bargaining"))
@pytest.mark.parametrize(
    "raw, category, bad",
    ((-1.0, RawPayoffCategory.NEGATIVE, True), (0.0, RawPayoffCategory.ZERO, True), (1.0, RawPayoffCategory.POSITIVE, False)),
)
def test_negotiation_and_bargaining_use_raw_zero_boundary(
    family: str, raw: float, category: RawPayoffCategory, bad: bool
) -> None:
    result = bad_outcome(family, raw, {}, None)
    assert result.category == category
    assert result.bad is bad


@pytest.mark.parametrize("role", ("buyer", "seller"))
@pytest.mark.parametrize(
    "raw, category, bad",
    ((-1.0, RawPayoffCategory.NEGATIVE, True), (0.0, RawPayoffCategory.ZERO, True), (1.0, RawPayoffCategory.POSITIVE, False)),
)
def test_persuasion_distinguishes_negative_zero_and_positive_by_role(
    role: str, raw: float, category: RawPayoffCategory, bad: bool
) -> None:
    result = bad_outcome("persuasion", raw, {}, role)
    assert result.role == role
    assert result.category == category
    assert result.bad is bad


def test_persuasion_requires_mechanism_role() -> None:
    with pytest.raises(ValueError):
        bad_outcome("persuasion", 0.0, {}, None)

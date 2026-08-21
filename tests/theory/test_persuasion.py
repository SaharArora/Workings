from theory.persuasion.baselines import (
    babbling_buyer_buys,
    commitment_low_signal_probability,
    commitment_value,
    full_disclosure_buyer_buys,
)


def test_reference_levels_hand_computed() -> None:
    assert babbling_buyer_buys(0.5, 2.0)
    assert not babbling_buyer_buys(0.49, 2.0)
    assert full_disclosure_buyer_buys("high")
    assert not full_disclosure_buyer_buys("low")
    assert commitment_low_signal_probability(0.25, 2.0) == 1 / 3
    assert commitment_value(0.75, 2.0) == 1.0

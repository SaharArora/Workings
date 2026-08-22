from scripts.generate_behavioral_pilot_report import _aggregate_table


def test_structural_report_groups_scaled_cells_without_losing_exact_results() -> None:
    common = {
        "role": "buyer",
        "selected_policy": "NEGOTIATION_ADAPTIVE",
        "structural_policy_class": (
            "negotiation/incomplete-info/unknown-horizon/buyer/NEGOTIATION_ADAPTIVE"
        ),
        "outcome": "walked_away",
        "raw_payoff": 0,
        "scale_adjusted_payoff": 0.5,
        "rating_before": 1000,
        "rating_after": 999,
        "opponent": {"type": "hidden"},
    }
    rows = [
        {**common, "cell": "value=100"},
        {**common, "cell": "value=1000000", "opponent": {"type": "agent"}},
    ]
    structural = "\n".join(_aggregate_table(rows, structural=True))
    exact = "\n".join(_aggregate_table(rows, structural=False))
    assert structural.count("NEGOTIATION_ADAPTIVE") >= 1
    assert "| 2 |" in structural
    assert "value=100" in exact
    assert "value=1000000" in exact

from theory.negotiation.baselines import bayes_optimal_posted_price, complete_information_price


def test_no_trade_first_order_decomposition() -> None:
    assert complete_information_price(10, 8, max_rounds=1) is None


def test_complete_information_rows() -> None:
    assert complete_information_price(10, 15, max_rounds=1) == 15
    assert complete_information_price(10, 15, max_rounds=3) == 15
    assert complete_information_price(10, 15, max_rounds=10) == 10
    assert complete_information_price(10, 15, max_rounds=None) == 12.5


def test_bayes_posted_price_hand_computed() -> None:
    # At p=12 payoff is 2; p=15 succeeds half the time for expected 2.5.
    assert bayes_optimal_posted_price(10, {12: 0.5, 15: 0.5}, [10, 12, 15]) == 15

"""Fixed complete-information gains-from-trade concession."""

SURPLUS_CONCESSION = 0.15


def fairness_margin_price(seller_value: float, buyer_value: float, *, extractor: str) -> float | None:
    if buyer_value < seller_value:
        return None
    surplus = buyer_value - seller_value
    if extractor == "seller":
        return buyer_value - SURPLUS_CONCESSION * surplus
    if extractor == "buyer":
        return seller_value + SURPLUS_CONCESSION * surplus
    raise ValueError("extractor must be seller or buyer")

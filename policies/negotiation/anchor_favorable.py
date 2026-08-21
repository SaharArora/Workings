"""Own-favorable point in the unlimited complete-information equilibrium continuum."""

OWN_FAVORABLE_SHARE = 0.65


def own_favorable_price(seller_value: float, buyer_value: float, *, role: str) -> float | None:
    if buyer_value < seller_value:
        return None
    surplus = buyer_value - seller_value
    if role == "seller":
        return seller_value + OWN_FAVORABLE_SHARE * surplus
    if role == "buyer":
        return seller_value + (1 - OWN_FAVORABLE_SHARE) * surplus
    raise ValueError("role must be seller or buyer")

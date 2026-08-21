"""Fixed historical opening-anchor corrections for incomplete-information T=1."""

BUYER_OPENING_SHADE = 1.25
SELLER_OPENING_MARKUP = 1.50


def inferred_buyer_value(opening_offer: float) -> float:
    return opening_offer / BUYER_OPENING_SHADE


def inferred_seller_value(opening_ask: float) -> float:
    return opening_ask / SELLER_OPENING_MARKUP

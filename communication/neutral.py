"""One fixed non-strategic placeholder shared by both research variants."""

NEUTRAL_MESSAGE = "Acknowledged."
INTERNAL_MESSAGE_LIMIT = 1_800


def neutral_message() -> str:
    return NEUTRAL_MESSAGE[:INTERNAL_MESSAGE_LIMIT]

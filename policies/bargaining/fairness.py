"""Fixed fairness concession applied to a cell's own theoretical baseline."""

FAIRNESS_CONCESSION = 0.10


def fair_share(theory_proposer_share: float) -> float:
    return theory_proposer_share - FAIRNESS_CONCESSION * (theory_proposer_share - 0.5)

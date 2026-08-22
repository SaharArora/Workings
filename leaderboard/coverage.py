"""Machine-readable reachable configuration-class coverage for production routing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ConfigurationCoverage:
    family: str
    configuration_signature: str
    role: str
    theory_incumbent: str
    challenger: str | None
    required_runtime_inputs: tuple[str, ...]
    all_required_inputs_available: bool
    selected_incumbent: str
    executable: bool
    tested_offline: bool
    tested_live: bool
    deployment_status: str
    incomplete_classification: str | None = None

    def structured(self) -> dict[str, Any]:
        value = asdict(self)
        value["required_runtime_inputs"] = list(self.required_runtime_inputs)
        return value


def _live_verified(family: str, signature: str, role: str) -> bool:
    """Classes exercised by the frozen 2026-08-22 MVL pilots."""
    if family == "negotiation":
        if "information=complete;horizon=T=1;messages=true" in signature:
            return role == "seller"
        if "information=complete;horizon=unknown/unlimited;messages=true" in signature:
            return role == "seller"
        if "information=incomplete;horizon=T=1" in signature:
            return role == "buyer"
        if "information=incomplete;horizon=unknown/unlimited" in signature:
            return role == "seller" or (role == "buyer" and "messages=true" in signature)
    if family == "bargaining":
        return role == "bob" and any(
            marker in signature
            for marker in (
                "information=incomplete;horizon=finite;messages=true",
                "information=complete;horizon=unknown/unlimited;messages=false",
                "information=incomplete;horizon=unknown/unlimited;messages=false",
            )
        )
    if family == "persuasion":
        return (
            role == "buyer"
            and "message_type=text;seller_knows_buyer_values=false" in signature
        ) or (
            role == "seller"
            and "message_type=text;seller_knows_buyer_values=true" in signature
        )
    return False


def configuration_coverage() -> tuple[ConfigurationCoverage, ...]:
    """Enumerate policy-distinct classes in the documented current API grid.

    Numeric parameter values do not alter the policy path and are represented by named
    variables in each signature. Message availability is explicit because it changes the
    final rendering/validation path even when the economic incumbent is unchanged.
    """
    rows: list[ConfigurationCoverage] = []
    negotiation_horizons = {
        True: (
            ("T=1", "NEGOTIATION_COMPLETE_T1_THEORY"),
            ("finite odd T>1", "NEGOTIATION_COMPLETE_FINITE_ODD_THEORY"),
            ("finite even T", "NEGOTIATION_COMPLETE_FINITE_EVEN_THEORY"),
            ("unknown/unlimited", "NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT"),
        ),
        False: (
            ("T=1", "NEGOTIATION_INCOMPLETE_T1_ROBUST"),
            ("finite multi-round", "NEGOTIATION_ROBUST"),
            ("unknown/unlimited", "NEGOTIATION_ROBUST"),
        ),
    }
    for complete, horizons in negotiation_horizons.items():
        for horizon, selected in horizons:
            for role in ("seller", "buyer"):
                for messages in (False, True):
                    multi = not complete and horizon != "T=1"
                    theory = (
                        selected
                        if complete
                        else (
                            "NEGOTIATION_INCOMPLETE_T1_ROBUST"
                            if horizon == "T=1"
                            else "NEGOTIATION_INCOMPLETE_MULTIROUND_PORTFOLIO"
                        )
                    )
                    challenger = (
                        "fairness-margin-0.15 (not promoted)"
                        if complete and horizon in {"T=1", "finite odd T>1", "finite even T"}
                        else "anchor-favorable-0.65 (not promoted)"
                        if complete
                        else "trusted-prior Bayes/EMPIRICAL (prior unavailable; not promoted)"
                        if horizon == "T=1"
                        else "BAYES/EMPIRICAL (artifacts unavailable)"
                        if multi
                        else None
                    )
                    signature = (
                        f"information={'complete' if complete else 'incomplete'};"
                        f"horizon={horizon};messages={str(messages).lower()};"
                        "values=positive grid"
                    )
                    rows.append(
                        ConfigurationCoverage(
                            family="negotiation",
                            configuration_signature=signature,
                            role=role,
                            theory_incumbent=theory,
                            challenger=challenger,
                            required_runtime_inputs=(
                                ("own_value", "opponent_value", "valid_actions")
                                if complete
                                else ("own_value", "valid_actions")
                            ),
                            all_required_inputs_available=True,
                            selected_incumbent=selected,
                            executable=True,
                            tested_offline=True,
                            tested_live=_live_verified("negotiation", signature, role),
                            deployment_status="CLEAR",
                            incomplete_classification="RESEARCH_BLOCKED",
                        )
                    )

    for complete in (True, False):
        for horizon in ("finite", "unknown/unlimited"):
            for role in ("alice", "bob"):
                for messages in (False, True):
                    theory = (
                        ("BARGAINING_COMPLETE_FINITE" if horizon == "finite" else "BARGAINING_COMPLETE_UNLIMITED")
                        if complete
                        else (
                            "BARGAINING_INCOMPLETE_FINITE_BAYES_REFERENCE"
                            if horizon == "finite"
                            else "BARGAINING_INCOMPLETE_UNLIMITED_BAYES_REFERENCE"
                        )
                    )
                    selected = (
                        "BARGAINING_COMPLETE_FINITE"
                        if complete and horizon == "finite"
                        else "BARGAINING_COMPLETE_UNLIMITED"
                        if complete
                        else "BARGAINING_INCOMPLETE_EQUAL_SPLIT"
                    )
                    signature = (
                        f"information={'complete' if complete else 'incomplete'};"
                        f"horizon={horizon};messages={str(messages).lower()};"
                        "money=M;discounts=config-grid"
                    )
                    rows.append(
                        ConfigurationCoverage(
                            family="bargaining",
                            configuration_signature=signature,
                            role=role,
                            theory_incumbent=theory,
                            challenger="fairness-0.10 (not promoted)",
                            required_runtime_inputs=(
                                ("money_to_divide", "own_delta", "opponent_delta", "round", "valid_actions")
                                if complete
                                else ("money_to_divide", "last_offer_on_response", "valid_actions")
                            ),
                            all_required_inputs_available=True,
                            selected_incumbent=selected,
                            executable=True,
                            tested_offline=True,
                            tested_live=_live_verified("bargaining", signature, role),
                            deployment_status="CLEAR",
                            incomplete_classification="RESEARCH_BLOCKED",
                        )
                    )

    for message_type in ("text", "binary"):
        for seller_knows_values in (False, True):
            for role in ("seller", "buyer"):
                signature = (
                    f"message_type={message_type};seller_knows_buyer_values="
                    f"{str(seller_knows_values).lower()};history_aware_buyer=true;"
                    "rounds=T"
                )
                rows.append(
                    ConfigurationCoverage(
                        family="persuasion",
                        configuration_signature=signature,
                        role=role,
                        theory_incumbent="PERSUASION_P0_BABBLING",
                        challenger="P3 reputation (not promoted)",
                        required_runtime_inputs=(
                            ("seller_message_type", "valid_actions")
                            if role == "seller"
                            else ("p", "v", "u", "product_price", "valid_actions")
                        ),
                        all_required_inputs_available=True,
                        selected_incumbent="PERSUASION_P0_BABBLING",
                        executable=True,
                        tested_offline=True,
                        tested_live=_live_verified("persuasion", signature, role),
                        deployment_status="CLEAR",
                        incomplete_classification="RESEARCH_BLOCKED",
                    )
                )
    return tuple(rows)

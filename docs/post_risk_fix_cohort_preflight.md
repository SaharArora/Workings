# POST_RISK_FIX_RANDOMIZED_3000 preflight

Frozen registry hash: `fd045b13c86e9071bfd0ee1fbfb458e7d6594b0bca4053022a3169e4fb383a52`.

| Experiment | Stage | Priority | Control | Challenger | P(challenger) | alpha family/test | M | Threshold | delta | Status |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---|
| `NEG_INCOMPLETE_IBO_VS_ROBUST` | exploration | 1 | `NEGOTIATION_ROBUST` | `NEGOTIATION_ADAPTIVE` | 0.5 | 0.050/0.025 | 2 | 40 | 0.01 | RUNNING |
| `NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY` | exploration | 2 | `CONFIGURATION_SPECIFIC_THEORY` | `NEGOTIATION_FAIRNESS_MARGIN` | 0.5 | 0.050/0.025 | 2 | 40 | 0.01 | RUNNING |
| `BARG_COMPLETE_FAIRNESS_VS_THEORY` | exploration | 1 | `CONFIGURATION_SPECIFIC_THEORY` | `BARGAINING_FAIRNESS` | 0.5 | 0.050/0.050 | 1 | 20 | 0.01 | RUNNING |
| `PERS_BUY_MARGIN_VS_THEORY` | exploration | 1 | `PERSUASION_BUY_THEORY` | `PERSUASION_BUY_MARGIN` | 0.5 | 0.050/0.025 | 2 | 40 | 0.01 | RUNNING |
| `PERS_SELL_EMPIRICAL_VS_P0` | exploration | 2 | `PERSUASION_P0_BABBLING` | `PERSUASION_POOLED_EMPIRICAL` | 0.5 | 0.050/0.025 | 2 | 40 | 0.01 | RUNNING |
| `CONFIRM_NEG_INCOMPLETE_IBO_VS_ROBUST` | confirmation | 1 | `NEGOTIATION_ROBUST` | `NEGOTIATION_ADAPTIVE` | 0.5 | 0.050/0.050 | 1 | 20 | 0.01 | NOT_STARTED |
| `CONFIRM_NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY` | confirmation | 2 | `CONFIGURATION_SPECIFIC_THEORY` | `NEGOTIATION_FAIRNESS_MARGIN` | 0.5 | 0.050/0.050 | 1 | 20 | 0.01 | NOT_STARTED |
| `CONFIRM_BARG_COMPLETE_FAIRNESS_VS_THEORY` | confirmation | 1 | `CONFIGURATION_SPECIFIC_THEORY` | `BARGAINING_FAIRNESS` | 0.5 | 0.050/0.050 | 1 | 20 | 0.01 | NOT_STARTED |
| `CONFIRM_PERS_BUY_MARGIN_VS_THEORY` | confirmation | 1 | `PERSUASION_BUY_THEORY` | `PERSUASION_BUY_MARGIN` | 0.5 | 0.050/0.050 | 1 | 20 | 0.01 | NOT_STARTED |
| `CONFIRM_PERS_SELL_EMPIRICAL_VS_P0` | confirmation | 2 | `PERSUASION_P0_BABBLING` | `PERSUASION_POOLED_EMPIRICAL` | 0.5 | 0.050/0.050 | 1 | 20 | 0.01 | NOT_STARTED |

## Eligibility, payoff transforms, and bad events

- `NEG_INCOMPLETE_IBO_VS_ROBUST`: eligible=incomplete negotiation, finite multi-round or unknown horizon; payoff transform=`family_bounded_payoff_v1`; BAD_OUTCOME=raw own payoff <= 0 (negative, zero-margin agreement, no-deal, or walkaway).
- `NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY`: eligible=complete negotiation with finite, mathematically defined extraction; payoff transform=`family_bounded_payoff_v1`; BAD_OUTCOME=raw own payoff <= 0 (negative, zero-margin agreement, no-deal, or walkaway).
- `BARG_COMPLETE_FAIRNESS_VS_THEORY`: eligible=complete-information bargaining; payoff transform=`family_bounded_payoff_v1`; BAD_OUTCOME=raw own mechanism utility <= 0 (zero/no-deal/walkaway or negative).
- `PERS_BUY_MARGIN_VS_THEORY`: eligible=persuasion buyer states with visible p,v,u,price,total_rounds; payoff transform=`family_bounded_payoff_v1`; BAD_OUTCOME=raw realized buyer utility <= 0, with negative/zero retained separately; raw seller payoff <= 0 (zero/no-sale or negative).
- `PERS_SELL_EMPIRICAL_VS_P0`: eligible=persuasion seller states with visible p,v,u,positive price,total_rounds; payoff transform=`family_bounded_payoff_v1`; BAD_OUTCOME=raw realized buyer utility <= 0, with negative/zero retained separately; raw seller payoff <= 0 (zero/no-sale or negative).
- `CONFIRM_NEG_INCOMPLETE_IBO_VS_ROBUST`: eligible=incomplete negotiation, finite multi-round or unknown horizon; payoff transform=`family_bounded_payoff_v1`; BAD_OUTCOME=raw own payoff <= 0 (negative, zero-margin agreement, no-deal, or walkaway).
- `CONFIRM_NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY`: eligible=complete negotiation with finite, mathematically defined extraction; payoff transform=`family_bounded_payoff_v1`; BAD_OUTCOME=raw own payoff <= 0 (negative, zero-margin agreement, no-deal, or walkaway).
- `CONFIRM_BARG_COMPLETE_FAIRNESS_VS_THEORY`: eligible=complete-information bargaining; payoff transform=`family_bounded_payoff_v1`; BAD_OUTCOME=raw own mechanism utility <= 0 (zero/no-deal/walkaway or negative).
- `CONFIRM_PERS_BUY_MARGIN_VS_THEORY`: eligible=persuasion buyer states with visible p,v,u,price,total_rounds; payoff transform=`family_bounded_payoff_v1`; BAD_OUTCOME=raw realized buyer utility <= 0, with negative/zero retained separately; raw seller payoff <= 0 (zero/no-sale or negative).
- `CONFIRM_PERS_SELL_EMPIRICAL_VS_P0`: eligible=persuasion seller states with visible p,v,u,positive price,total_rounds; payoff transform=`family_bounded_payoff_v1`; BAD_OUTCOME=raw realized buyer utility <= 0, with negative/zero retained separately; raw seller payoff <= 0 (zero/no-sale or negative).

Every exploration/confirmation assignment is a fresh 50/50 draw persisted before the first treatment-dependent action. Confirmation rows are predeclared `NOT_STARTED`, use fresh games and M=1, and activate only after the corresponding exploration becomes `PROMOTION_CANDIDATE`.

## Prior bargaining cohort

`PRE_RISK_FIX_BARGAINING_200` contributes randomized=0, observational=200, excluded=1. It is not promotion evidence because no pre-treatment randomized assignment existed.

## Locked safety and reporting

A challenger safety-pauses if its first five valid challenger outcomes are all bad, or once n_challenger>=8 when its bad-outcome rate is strictly above 0.75. Integrity failures pause immediately. Family execution nevertheless continues observationally or through another unresolved experiment to exactly 1,000 completed games. Checkpoints at 200/500/750 are read-only.

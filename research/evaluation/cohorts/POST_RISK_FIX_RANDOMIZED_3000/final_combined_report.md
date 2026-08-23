TOTAL COMPLETED NEW GAMES = 2312 | BARGAINING = 1000 | NEGOTIATION = 1000 | PERSUASION = 312

# Final randomized cohort report

Cohort status: **TRUNCATED_BY_USER**.
Frozen cohort commit: `5229b9b771ef6702af63e61e214fcaeaf7a13176`. Registry hash: `fd045b13c86e9071bfd0ee1fbfb458e7d6594b0bca4053022a3169e4fb383a52`.
Original target: 3000. Completion shortfall: bargaining=0, negotiation=0, persuasion=688.
A family below target is not presented as a completed 1,000-game tranche; its unresolved experiment states are frozen at shutdown.

## Bargaining

Completed: 1000/1000. Randomized: 486. Observational: 514. Excluded: 0.
Run status: `COMPLETED_EXACT_CAP`. Target met: True.
Rating: 1698.79 -> 1552.54 (change -146.25).

| Experiment | Status | n control | n challenger | E | E mirror | Y effect | Raw effect |
|---|---|---:|---:|---:|---:|---:|---:|
| `BARG_COMPLETE_FAIRNESS_VS_THEORY` | INCONCLUSIVE | 246 | 240 | 0.219819 | 0.12742 | 0.0183878 | 45031.7 |
| `CONFIRM_BARG_COMPLETE_FAIRNESS_VS_THEORY` | NOT_STARTED | 0 | 0 | 1 | 1 | 0 | 0 |

## Negotiation

Completed: 1000/1000. Randomized: 182. Observational: 818. Excluded: 0.
Run status: `COMPLETED_EXACT_CAP`. Target met: True.
Rating: 978.14 -> 1167.01 (change 188.87).

| Experiment | Status | n control | n challenger | E | E mirror | Y effect | Raw effect |
|---|---|---:|---:|---:|---:|---:|---:|
| `CONFIRM_NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY` | NOT_STARTED | 0 | 0 | 1 | 1 | 0 | 0 |
| `CONFIRM_NEG_INCOMPLETE_IBO_VS_ROBUST` | NOT_STARTED | 0 | 0 | 1 | 1 | 0 | 0 |
| `NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY` | INCONCLUSIVE | 82 | 85 | 0.360242 | 0.180284 | 0.0115772 | -6390.5 |
| `NEG_INCOMPLETE_IBO_VS_ROBUST` | SAFETY_PAUSED | 10 | 5 | 0.363696 | 1.85994 | 0 | 0 |

## Persuasion

Completed: 312/1000. Randomized: 135. Observational: 177. Excluded: 46.
Run status: `TRUNCATED_BY_USER_AT_312`. Target met: False.
Rating: 1383.34 -> 1472.10 (change 88.76).

| Experiment | Status | n control | n challenger | E | E mirror | Y effect | Raw effect |
|---|---|---:|---:|---:|---:|---:|---:|
| `CONFIRM_PERS_BUY_MARGIN_VS_THEORY` | NOT_STARTED | 0 | 0 | 1 | 1 | 0 | 0 |
| `CONFIRM_PERS_SELL_EMPIRICAL_VS_P0` | NOT_STARTED | 0 | 0 | 1 | 1 | 0 | 0 |
| `PERS_BUY_MARGIN_VS_THEORY` | SAFETY_PAUSED | 2 | 5 | 1.12403 | 0.556122 | -0.206667 | -1.25e+06 |
| `PERS_SELL_EMPIRICAL_VS_P0` | RUNNING | 38 | 44 | 3.24346 | 0.0818492 | 0.19988 | 888179 |

## Shutdown and integrity

Active games: 0. Pending games: 0.
The JSON companion contains arm distributions, opponent and structural-cell diagnostics, operational failures/fallbacks/timeouts, clipping, and deterministic e-process replay state.

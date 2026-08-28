# Leaderboard chart snapshots

Charts-only, read-only snapshots from the live leaderboard campaigns. This
branch excludes credentials, assignment secrets, game-level tables, runtime
databases, process locks, and raw game state.

## GangsterYoshi Phase A V16

Snapshot refreshed `2026-08-28T20:29:51.206291+00:00`, after 363 fresh V16
games in each family. At that snapshot there were 550 evidence updates, zero
incidents, zero promotion candidates, and zero promotions.

- [Bargaining rating](gangsteryoshi-v16/bargaining-rating.svg)
- [Bargaining payoff](gangsteryoshi-v16/bargaining-payoff.svg)
- [Bargaining policy behavior](gangsteryoshi-v16/bargaining-behavior.svg)
- [Negotiation rating](gangsteryoshi-v16/negotiation-rating.svg)
- [Negotiation payoff](gangsteryoshi-v16/negotiation-payoff.svg)
- [Negotiation policy behavior](gangsteryoshi-v16/negotiation-behavior.svg)
- [Persuasion rating](gangsteryoshi-v16/persuasion-rating.svg)
- [Persuasion payoff](gangsteryoshi-v16/persuasion-payoff.svg)
- [Persuasion policy behavior](gangsteryoshi-v16/persuasion-behavior.svg)

Unit-level e-process charts are in
[`gangsteryoshi-v16/eprocess/`](gangsteryoshi-v16/eprocess/).

## YakuzaYoshi Phase B V22 validation

The excluded THEORY and EXPLOIT canary coverage passed and ordinary validation
traffic began automatically. This initial snapshot was generated
`2026-08-28T20:28:51.645746+00:00`; it plots 17 bargaining, 12 negotiation, and
12 persuasion matches (including excluded canaries), with 11 visible policy-arm
switches. Ordinary volume continues toward 1,000 fresh completed games in each
family.

Every plot labels the x-axis **Games played** and the y-axis **Leaderboard
rating**. Orange points are whole-game THEORY, blue points are whole-game
EXPLOIT, and dashed purple lines mark policy changes between consecutive
matches.

- [Bargaining rating and policy](yakuzayoshi-v22/bargaining-rating.svg)
- [Negotiation rating and policy](yakuzayoshi-v22/negotiation-rating.svg)
- [Persuasion rating and policy](yakuzayoshi-v22/persuasion-rating.svg)

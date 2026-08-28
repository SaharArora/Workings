# Leaderboard chart snapshots

Charts-only, read-only snapshots from the live leaderboard campaigns. This
branch excludes credentials, assignment secrets, game-level tables, runtime
databases, process locks, and raw game state.

## GangsterYoshi Phase A V16

Snapshot generated `2026-08-28T19:02:04.729099+00:00`, after 321 fresh V16
bargaining games, 321 negotiation games, and 320 persuasion games. At that
snapshot there were 486 evidence updates, zero incidents, and zero promotions.

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

Yakuzayoshi charts will be added after its excluded Phase B canaries pass and
ordinary validation volume begins. Its minimum target is 1,000 fresh completed
games in each family.

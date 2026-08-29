# Leaderboard chart snapshots

Read-only, sanitized chart snapshots. Credentials, assignment secrets, game IDs, raw game state, databases, and process locks are not published.

Orange points are whole-game **THEORY** and blue points are whole-game **EXPLOIT**. Rating and payoff charts have numeric axes; payoff charts mark `0.00` explicitly. Public files are replaced on a 30-minute cadence when their source data changes.

## GangsterYoshi Phase B V29

Latest completed game: `2026-08-29T23:52:10.203635+00:00`. Charted V29 ordinary live games: bargaining 0, negotiation 3, persuasion 0.

Bargaining and persuasion refill independently. Negotiation uses the byte-identical V28 role route under a durable 25+25 positive-rating checkpoint, a 15-point drawdown floor, and a 50-game hard maximum.

- [Bargaining rating](gangsteryoshi-v29/bargaining-rating.svg)
- [Bargaining payoff](gangsteryoshi-v29/bargaining-payoff.svg)
- [Bargaining configuration and policy](gangsteryoshi-v29/bargaining-configuration-policy.svg)
- [Negotiation rating](gangsteryoshi-v29/negotiation-rating.svg)
- [Negotiation payoff](gangsteryoshi-v29/negotiation-payoff.svg)
- [Negotiation configuration and policy](gangsteryoshi-v29/negotiation-configuration-policy.svg)
- [Persuasion rating](gangsteryoshi-v29/persuasion-rating.svg)
- [Persuasion payoff](gangsteryoshi-v29/persuasion-payoff.svg)
- [Persuasion configuration and policy](gangsteryoshi-v29/persuasion-configuration-policy.svg)

## YakuzaYoshi Phase B V25 validation

Latest completed game: `2026-08-29T18:26:47.186118+00:00`. Charted games (excluded canaries plus ordinary validation): bargaining 494, negotiation 747, persuasion 487.

The configuration-policy charts put games on the x-axis and the registered Appendix A.1 strategic configuration unit on the y-axis. Point color shows the exact whole-game arm used.

- [Bargaining rating and policy](yakuzayoshi-v25/bargaining-rating.svg)
- [Bargaining configuration and policy](yakuzayoshi-v25/bargaining-configuration-policy.svg)
- [Negotiation rating and policy](yakuzayoshi-v25/negotiation-rating.svg)
- [Negotiation configuration and policy](yakuzayoshi-v25/negotiation-configuration-policy.svg)
- [Persuasion rating and policy](yakuzayoshi-v25/persuasion-rating.svg)
- [Persuasion configuration and policy](yakuzayoshi-v25/persuasion-configuration-policy.svg)

# Leaderboard chart snapshots

Read-only, sanitized chart snapshots. Credentials, assignment secrets, game IDs, raw game state, databases, and process locks are not published.

Orange points are whole-game **THEORY** and blue points are whole-game **EXPLOIT**. Rating and payoff charts have numeric axes; payoff charts mark `0.00` explicitly. Public files are replaced on a 30-minute cadence when their source data changes.

## GangsterYoshi Phase B V37

Latest completed game: `2026-08-30T12:03:42.033934+00:00`. Charted V37 ordinary live games: bargaining 19, negotiation 10, persuasion 0.

Persuasion is intentionally disabled with target zero. Bargaining and negotiation refill independently; bargaining stops only below 2,005. Negotiation is capped at 50 rated games, stops at or below 1,625, and enters its second tranche only if its 25-game rating is strictly above the V37 baseline; at most three unrated invalid-move terminals are excluded.

- [Bargaining rating](gangsteryoshi-v37/bargaining-rating.svg)
- [Bargaining payoff](gangsteryoshi-v37/bargaining-payoff.svg)
- [Bargaining configuration and policy](gangsteryoshi-v37/bargaining-configuration-policy.svg)
- [Negotiation rating](gangsteryoshi-v37/negotiation-rating.svg)
- [Negotiation payoff](gangsteryoshi-v37/negotiation-payoff.svg)
- [Negotiation configuration and policy](gangsteryoshi-v37/negotiation-configuration-policy.svg)
- [Persuasion rating](gangsteryoshi-v37/persuasion-rating.svg)
- [Persuasion payoff](gangsteryoshi-v37/persuasion-payoff.svg)
- [Persuasion configuration and policy](gangsteryoshi-v37/persuasion-configuration-policy.svg)

## YakuzaYoshi Phase B V25 validation

Latest completed game: `2026-08-29T18:26:47.186118+00:00`. Charted games (excluded canaries plus ordinary validation): bargaining 494, negotiation 747, persuasion 487.

The configuration-policy charts put games on the x-axis and the registered Appendix A.1 strategic configuration unit on the y-axis. Point color shows the exact whole-game arm used.

- [Bargaining rating and policy](yakuzayoshi-v25/bargaining-rating.svg)
- [Bargaining configuration and policy](yakuzayoshi-v25/bargaining-configuration-policy.svg)
- [Negotiation rating and policy](yakuzayoshi-v25/negotiation-rating.svg)
- [Negotiation configuration and policy](yakuzayoshi-v25/negotiation-configuration-policy.svg)
- [Persuasion rating and policy](yakuzayoshi-v25/persuasion-rating.svg)
- [Persuasion configuration and policy](yakuzayoshi-v25/persuasion-configuration-policy.svg)

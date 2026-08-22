# MVL deployment-readiness report

## 1. Current commit

Frozen deployment/pilot commit: `49a6021726553425506a09e23798b813c6091d9a`. Subsequent commits contain only pilot transcripts, live-coverage metadata, and reports; they do not alter the frozen policies.

## 2. DEPLOYMENT_BLOCKER vs RESEARCH_BLOCKED classification

No deployment blocker remains. Missing priors/artifacts, untrained BAYES/EMPIRICAL, unpromoted challengers, promotion evidence, and communication optimization are research-blocked only because every reachable class has a tested incumbent.

## 3. Full configuration-coverage matrix

See `docs/configuration_coverage.md` and `.json`: 52/52 classes are offline tested; the classes encountered in these pilots are marked live tested.

## 4. II/T=1 negotiation audit

Current API payloads expose no trusted value prior. Current incomplete T=1 uses the intentional one-shot ROBUST incumbent. An explicitly supplied future discrete prior would optimize over its own finite support, not an invented price grid.

## 5. Implementation changes required for coverage

Named incomplete-bargaining equal split; proposer/remaining-round bargaining fixes; general-price P0 buyer rule; local action-schema validation; exact pilot lifecycle and stop control; and intentional unknown-horizon cycle exits for all relevant incumbents.

## 6. Latency benchmark by family/policy

See `docs/latency_benchmark.md`. All 14 offline paths pass p95 <= 10s/max <= 30s. Live family p95/max (ms): negotiation 1.2327/3.6666; bargaining 2.1858/2.1858; persuasion 0.5192/3.4058.

## 7. Credential/repository hygiene result

VERIFIED: `.env` ignored/untracked, example empty, and no current credential in tracked files, Git refs, or any pilot transcript.

## 8. Frozen pilot commit

`49a6021726553425506a09e23798b813c6091d9a`; unchanged across all 16 qualifying games.

## 9. 10-game negotiation pilot results by cell/role

10/10 complete; zero hard stops/fallbacks/invalid actions/strategic events. See `docs/pilot_negotiation_report.md`.

## 10. Bargaining pilot results

3/3 complete; zero hard stops/fallbacks/invalid actions/strategic events. See `docs/pilot_bargaining_report.md`.

## 11. Persuasion pilot results

3/3 complete; zero hard stops/fallbacks/invalid actions/strategic events. See `docs/pilot_persuasion_report.md`.

## 12. Hard-stop events

None in the qualifying pilots. Two earlier negotiation attempts were invalidated and retained because they exposed/fixed the unknown-horizon cycle deployment gap.

## 13. Strategic-review events

None. One negotiation cell/role had 2/2 floor outcomes, below the predeclared n=3 trigger.

## 14. NEGOTIATION_MVL_READY: yes

10/10 qualifying games, every route intentional, zero operational events, safe latency.

## 15. BARGAINING_MVL_READY: yes

3/3 qualifying games, including incomplete equal split and unknown-horizon theory, with zero operational events.

## 16. PERSUASION_MVL_READY: yes

3/3 qualifying repeated games across buyer/seller paths with zero operational events.

## 17. ALL_FAMILIES_MVL_READY: yes

This authorizes no continuous execution; it only satisfies the declared readiness gate.

## 18. Remaining RESEARCH_BLOCKED items

BAYES historical support/artifacts; EMPIRICAL training/promotion; LLM-vs-LLM ingest; e-process promotion evidence; P3 trust-rate artifact; strategic communication and receiver modeling; and evaluation of ROBUST's observed zero-payoff negotiation behavior.

## 19. Active/pending games after shutdown

`active_games=0`, `pending_games=0`; all queues explicitly left.

## 20. Recommended next action (not executed)

After explicit human approval, deploy a still-bounded, monitored volume tranche while grouping outcomes by cell/role and prioritizing research on the repeated zero-payoff ROBUST cells. Do not start persistent execution yet.

# Verification log

Mechanism and SDK facts marked VERIFY-FIRST in `BUILD_SPEC.md` are recorded here before
dependent implementation.

## Status vocabulary

`CONFIRMED`, `CONTRADICTED`, or `BLOCKED`.

## 1. Negotiation finite-horizon parity mechanics

- **item:** Alice proposes odd stages, Bob even stages, numbering begins at 1, and Bob
  is the terminal proposer when `max_rounds=10`.
- **source inspected:** Official `glee-sdk` v0.0.5 README/client source and GLEE reference
  implementation `games/negotiation/negotiation.py` on `eilamshapira/GLEE@master`.
- **result:** `CONFIRMED`
- **evidence:** The reference loop is `range(1, max_rounds + 1)` and selects player 1
  when `round_number % 2`, otherwise player 2. The SDK documents 1-based `round` and the
  final-round no-counteroffer behavior. Therefore round 10 is proposed by player 2/Bob.
- **dependent components:** Complete-information finite-even negotiation baseline.
- **action taken:** Finite-even theory implementation is permitted as specified.

## 2. Negotiation legal price domain

- **item:** Whether `product_price` has a finite mechanism-defined domain and whether `M`
  or `product_price_order` supplies its endpoints.
- **source inspected:** GLEE paper §2.2 footnote 6; original GLEE validator at commit
  `68a33e98b035b97f945badee8f325001555c0049`; original oTree form and negotiation-bot
  maximum hook; historical configuration generator/examples; official `glee-sdk` v0.0.5
  source/README at commit `2a80ef560a603968118b6236067c06fd2e513410`; current competition
  `llms.txt` and production human UI bundle; first controlled canary payload.
- **result:** `CONTRADICTED` — **finding status:** `VERIFIED` (no finite upper bound)
- **evidence:** The paper states that accepted negotiation price `p_ev` is “unbounded in
  principle.” It separately defines valuations as `V_i=M*F_i`; `M` is a valuation scale,
  not an action cap. The original validator (`games/negotiation/negotiation.py:201-216`)
  only accepts numeric/string-numeric input and performs no sign, magnitude, minimum, or
  maximum check. `product_price_order` multiplies seller/buyer valuation only
  (`:15,20-21`). The original human form uses `IntegerField(min=0)` without a maximum and
  its negotiation bot returns `get_max_offer() = None`. The current production human UI
  rejects non-finite/negative values and renders `min=0` with no `max`. The current SDK
  forwards the action unchanged, and SDK/current API docs describe only a numeric price.
  Historical configs contain no price endpoints. Thus there is definitively no finite
  mechanism `p_max`, and `M` must not be substituted. The exact lower-bound rule of the
  unpublished current *agent API* remains unresolved: original LLM validation accepts
  negative numerics, while original/current human clients enforce zero; current agent
  docs/live `valid_actions` say only `number`. This lower-bound uncertainty cannot restore
  a bounded domain because the upper endpoint is verified absent.
- **dependent components:** Negotiation payoff-bound instantiation in
  `glee/normalization.py` and any live legal-price grid construction.
- **action taken:** The finite-bound assumption is rejected rather than left unknown.
  `glee/normalization.py` now raises `UnboundedPayoffDomainError` for negotiation even if
  a configured/observed finite range is passed; its finite formula is retained only as an
  explicitly counterfactual helper for a future independently bounded mechanism. The
  separately labeled clipped statistical payoff transform now supplies bounded research
  scores without changing that mechanism finding. ROBUST likewise does not fabricate a
  mechanism grid; it uses a finite policy-generated decision set. No rated-game
  extreme-price probing was performed.

## Unbounded-domain ROBUST and negotiation statistical transform

- **item:** Make ROBUST executable without a finite legal `p_max` and bound negotiation
  research outcomes without calling the result mechanism normalization.
- **source inspected:** Verified unbounded-domain finding above and the explicitly locked
  follow-up design for policy candidates, scenarios, clipping, and `delta_min` semantics.
- **result:** `CONFIRMED`
- **evidence:** Seller policy candidates are fixed multiples through `2V_S`; buyer
  candidates are fixed fractions through `V_B`. Corresponding deterministic valuation
  scenarios feed minimax regret, and agreement-favorable ties are fixed. No finite legal
  upper endpoint is consumed. The statistical transform records raw `U` and computes
  `S=max(|V_i|,1)`, `C=2S`, and `Y=(clip(U,-C,C)+C)/(2C)`.
- **dependent components:** `policies/negotiation/robust.py`, policy router, research
  experiment logging/evaluation, and negotiation e-process inputs.
- **action taken:** ROBUST uses its policy-generated set and deterministic current-offer
  rule. Negotiation experiments must use `observe_negotiation`, which recomputes and
  validates the transform before betting; raw utility, transform metadata, and clipping
  status remain in the append-only record. `delta_min=.01` now estimates improvement in
  expected clipped scale-adjusted utility and corresponds locally, only before clipping,
  to `.04S` raw utility.

## 3. SDK transport interface and credential variable

- **item:** Package/class/method surface and API credential environment variable.
- **source inspected:** Official `eilamshapira/GLEE_competition` SDK source at v0.0.5,
  `sdk/glee_sdk/client.py`, `sdk/glee_sdk/__init__.py`, examples, and `sdk/README.md`.
- **result:** `CONFIRMED`
- **evidence:** Package `glee_sdk` exports `GleeClient`; `run(strategy,
  game_families=None, poll_interval=2.0, max_games=None, max_time=None, requeue=True,
  concurrency=1)` owns queueing, polling, concurrent dispatch, draining, transport retry,
  and rate-limit backoff. Low-level methods are `queue`, `pending_games`, `move`,
  `game_state`, `stats`, and `leave_queue`. Official examples read `GLEE_API_KEY`.
- **dependent components:** `glee/client.py`, `glee/retry.py`, `.env.example`.
- **action taken:** Implemented a thin SDK adapter; local retry handles only strategy
  validation/fallback. `GLEE_API_TOKEN` is not used.

## 4. Opponent-type enum, disclosed-human case

- **item:** Literal disclosed-human category value.
- **source inspected:** Official `glee-sdk` v0.0.5 `pending_games` documentation and
  README payload schema.
- **result:** `CONFIRMED`
- **evidence:** Both directly state disclosed opponent type is `"agent"|"human"` and
  undisclosed is `"hidden"`.
- **dependent components:** Schemas, experiment stratification, policy router.
- **action taken:** Enum fixed to `human`, `agent`, and `hidden`.

## Live transport smoke test

- **item:** Queue, poll, stats, and leave-queue against the real API without making moves.
- **source inspected:** Official SDK v0.0.5 through controlled live rated canary
  `ba9c3e41-8b3a-4e77-8d81-d5b01abf17a7` on 2026-08-21.
- **result:** `CONFIRMED`
- **evidence:** Authenticated `stats()` and `pending_games()` succeeded before queueing;
  initial state was `active_games=0` with no pending games. One negotiation queue entry
  matched; polling returned the live state; one valid move was submitted; final
  `game_state()` returned completed agreement; `leave_queue()` ran on exit; final state
  was `active_games=0` with no pending games. Games played increased from 107 to 108.
- **dependent components:** Completion criterion for live API smoke testing.
- **action taken:** Live transport criterion is satisfied. No credential was logged.

## Controlled rated canary transcript summary

- **item:** Exactly one bounded end-to-end negotiation deployment canary.
- **source inspected:** Structured runtime log and terminal `game_state()` for game
  `ba9c3e41-8b3a-4e77-8d81-d5b01abf17a7`.
- **result:** `CONFIRMED`
- **evidence:** Configuration: incomplete information, unknown/unlimited horizon,
  messages allowed; role `player_1` seller with visible reservation value 10000; opponent
  category `hidden`; policy `theory_action`. Submitted
  `{"product_price":10000.0,"message":"I propose the stated price of 10000.0."}`;
  server marked it valid. Player 2 accepted in round 1. Terminal result: agreement at
  10000, player-1 payoff 0, player-2 payoff 2000. Fallback count: 0.
- **dependent components:** End-to-end production policy routing, strategic rendering,
  SDK transport, and never-raise boundary.
- **action taken:** Stopped after this single game; no experiment or persistent
  leaderboard run began. A verified SDK v0.0.5 edge case was observed: with
  `requeue=False`, a game completed by the opponent while not pending on our agent does
  not increment `run()`'s local `completed` counter, leaving the loop idle even though
  `active_games=0`. After confirming terminal completion, the loop was interrupted and
  its `finally` block left the queue. This is now handled generically by
  `glee/supervisor.py`, which independently tracks terminal game IDs and does not rely on
  the SDK counter for bounded execution.

## Second controlled rated canary — fixed router and supervisor

- **item:** Exactly one post-fix negotiation canary validating ROBUST routing and bounded
  automatic completion.
- **source inspected:** Structured route/action/supervisor stream and terminal
  `game_state()` for game `a52a6f07-d35a-4906-a2b4-d8317c1d1c57` on 2026-08-21.
- **result:** `CONFIRMED`
- **evidence:** Preflight returned `active_games=0` and no pending games. The single match
  was negotiation, incomplete information, unknown/unlimited horizon, messages allowed;
  our role was seller with visible reservation value 100 and opponent category `hidden`.
  The exact cell had no eligibility record, BAYES artifact, or promoted policy, so the
  structured route selected `NEGOTIATION_ROBUST` with
  `BAYES_ELIGIBILITY_UNAVAILABLE`—never the former generic `theory_action`. On both of our
  turns, ROBUST v1 could not construct its locked minimax-regret action because the live
  payload exposed `product_price: number` but no finite legal price or opponent-valuation
  grid. The recorded `PolicyInputsUnavailable` execution fallback therefore produced the
  predefined legal actions: first an offer at 100; after the hidden buyer rejected and
  counteroffered 45, `WalkAway`. The terminal result was `walked_away`, with player-1
  payoff 0 and player-2 payoff 0. Policy-execution fallback count was 2; outer
  `never_raise` fallback count was 0; every submission was valid.
- **dependent components:** Live configuration routing, fail-closed ROBUST execution,
  queue supervision, terminal accounting, and cleanup.
- **action taken:** `run_bounded(max_games=1, concurrency=1, requeue=False)` made one queue
  call, tracked and completed exactly this game, emitted `MAX_GAMES_COMPLETED`, ran queue
  cleanup, and returned automatically after 8.64 seconds. Postflight returned
  `active_games=0`, no pending games, and negotiation games played increased from 108 to
  109. No second queue/run, randomized experiment, or persistent leaderboard process was
  started. Live ROBUST *routing* is verified; ROBUST v1 action execution remains blocked
  pending an authorized formulation compatible with an unbounded price domain.

## Generic policy routing audit

- **item:** Configuration-specific incumbents and the underdetermined negotiation
  BAYES/ROBUST/EMPIRICAL hierarchy.
- **source inspected:** `BUILD_SPEC.md` §§4–5 and the first controlled canary route.
- **result:** `CONFIRMED`
- **evidence:** The original implementation used
  `policy_map.get((cell, opponent), theory_action)`. Thus every cell absent from the map
  entered one generic function; its incomplete-negotiation branch returned the current
  player's reservation value. This bypassed the specified underdetermined-cell incumbent
  selection entirely.
- **dependent components:** Leaderboard and research routing for all three families.
- **action taken:** Replaced the generic default with explicit configuration
  classification and structured `RoutingDecision` records. In incomplete multi-round or
  unknown-horizon negotiation, eligible BAYES plus a loadable frozen artifact selects
  BAYES; every unavailable-eligibility, ineligible, missing-artifact, or corrupt-artifact
  case selects ROBUST. Unavailable eligibility is logged as `null`, not misreported as a
  failed gate. EMPIRICAL requires an explicit promoted artifact. Bargaining retains its
  matching theory row and persuasion retains P0 absent a promotion. Unrecognized cells
  fail closed as `UNSUPPORTED_CELL`.
  The second controlled canary exercised the incomplete-information, unknown-horizon row
  live and confirmed selection of `NEGOTIATION_ROBUST` when BAYES metadata/artifacts were
  unavailable.

## Bounded-run lifecycle supervision

- **item:** Opponent-initiated completion and exact finite-run termination.
- **source inspected:** Official SDK v0.0.5 `GleeClient.run()` and first controlled
  canary runtime behavior.
- **result:** `CONFIRMED`
- **evidence:** The SDK increments its local `completed` counter only when `_handle_game`
  sees `game_over` in our own move response. An opponent can terminate between our turns,
  leaving no pending move for `_handle_game`; the API then reports `active_games=0` while
  the SDK counter remains unchanged.
- **dependent components:** Controlled canaries and all bounded leaderboard runs.
- **action taken:** Added an authoritative low-level supervisor that tracks each game ID,
  polls terminal game state, recognizes disappearance after tracking at active count zero,
  counts IDs once, prevents queue top-up when `requeue=False`, leaves queues during
  cleanup, and enforces a hard safety timeout.
  The second controlled canary counted one own-action terminal result exactly once and
  returned automatically with `MAX_GAMES_COMPLETED`; no manual interruption was needed.

## Historical negotiation data support

- **item:** Targeted-first negotiation ingestion and `n >= 200` BAYES gate.
- **source inspected:** `eilamshapira/GLEE@master`, complete
  `Data/human_vs_llm/negotiation` subtree and GitHub tree metadata for
  `Data/llm_vs_llm/negotiation`.
- **result:** `BLOCKED`
- **evidence:** Human-vs-LLM: 1,224 games, 30 exact cells, maximum 102 games/cell, so no
  exact cell is eligible. LLM-vs-LLM: tree response truncated at 80,454 entries after
  reporting 55,852 blobs / 47,408,482 bytes; two targeted sparse fetches failed with
  HTTP 400 from the promisor remote.
- **dependent components:** Per-cell BAYES fitting/eligibility, EMPIRICAL training, and
  data-derived persuasion reputation population rates.
- **action taken:** Implemented incremental ingestion; no synthetic training data is
  substituted. Data-trained artifacts/cells without support are marked blocked.

## Live policy experiments and confirmation

- **item:** Randomized prioritized live experiments, promotion, and fresh same-cell
  confirmation.
- **source inspected:** Controlled canary result and experiment registry.
- **result:** `BLOCKED`
- **evidence:** Authentication is now verified, but the only authorized live activity was
  one non-randomized deployment canary. The registry contains no completed randomized
  experiment, and no exact ingested negotiation cell satisfies the historical support
  gate for BAYES/EMPIRICAL testing.
- **dependent components:** Empirical promotions, same-cell confirmation, active
  non-default policy map, and real leaderboard deployment claims.
- **action taken:** The canary was not entered as experimental evidence. The auditable
  harness retains default incumbents and no candidate is represented as promoted.

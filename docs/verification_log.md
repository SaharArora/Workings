# Verification log

Mechanism and SDK facts marked VERIFY-FIRST in `BUILD_SPEC.md` are recorded here before
dependent implementation.

## Status vocabulary

Verification findings use `CONFIRMED`, `CONTRADICTED`, or `BLOCKED`; build reporting
retains `IMPLEMENTED`, `VERIFIED`, `BLOCKED`, and `NOT_YET_BUILT`. Incomplete/problematic
items additionally receive exactly one operational class when relevant:
`DEPLOYMENT_BLOCKER` if they can make live execution invalid, undefined, uncontrolled, or
unsafe in time; otherwise `RESEARCH_BLOCKED` when only an advanced strategy/evidence path
is unavailable.

## MVL configuration and input audit

- **item:** Intentional executable incumbents for every policy-distinct current API
  configuration class and role, including incomplete-information T=1 negotiation.
- **source inspected:** Current official competition `llms.txt` retrieved 2026-08-21,
  installed `glee-sdk==0.0.5`, original GLEE parameter generator, `BUILD_SPEC.md`, and all
  production routers/policies.
- **result:** `CONFIRMED` — 52/52 classes offline executable; 0 deployment blockers.
- **evidence:** Current incomplete negotiation payloads expose only own value and no prior;
  the historical grid is not a trusted distribution announced to the live agent. The
  trusted-prior T=1 formula is therefore non-executable (Case C), and current T=1 selects
  one-shot unbounded ROBUST without using learned BAYES eligibility. Current incomplete
  bargaining likewise exposes own discount only and no opponent prior; it now selects the
  intentional equal-split incumbent instead of raising into the emergency wrapper.
  Complete bargaining uses proposer/remaining-round-correct continuation logic, and P0
  persuasion consumes all actual expected-value fields on the buyer path.
- **classification:** Missing priors, BAYES/EMPIRICAL/P3 evidence, and unpromoted fixed
  deviations are `BLOCKED` or `NOT_YET_BUILT` + `RESEARCH_BLOCKED`; none removes the safe
  incumbent.
- **dependent artifacts:** `docs/configuration_coverage.json` and
  `docs/configuration_coverage.md`.

## Turn-time compliance

- **item:** End-to-end local latency of every production incumbent path.
- **source inspected:** Current official docs (120-second per-turn limit) and a 1,000-call
  benchmark per representative path including parsing, routing/policy computation,
  communication rendering, and action validation.
- **result:** `CONFIRMED`
- **evidence:** All 14 production paths pass p95 <= 10 seconds and maximum <= 30 seconds;
  observed values are in `docs/latency_benchmark.md` / `.json`. Network/API time is
  excluded and separately bounded by the SDK's 30-second request timeout/retry behavior.
- **classification:** No latency `DEPLOYMENT_BLOCKER`.

## Credential and repository hygiene

- **item:** Rotated live credential and runtime-artifact hygiene before increasing rated
  volume.
- **source inspected:** Git ignore/index/current tree/all refs and every current runtime
  artifact, compared locally without printing or serializing the secret.
- **result:** `CONFIRMED`
- **evidence:** `.env` is ignored and untracked; `.env.example` contains only an empty
  placeholder; the current rotated credential occurs in zero tracked files, zero runtime
  artifacts, and zero commits on current refs. No transcript contains it.
- **action taken:** No history rewrite was needed or performed. Pilot logging records
  states, actions, results, and commit metadata only; it never reads the credential.

## Aborted first MVL negotiation pilot — deterministic no-progress cycle

- **item:** Frozen 10-game negotiation pilot attempt on commit
  `023d8f4b5ae1966498be9241b06cb7f6a2df7e2b`.
- **result:** `CONTRADICTED` — `DEPLOYMENT_BLOCKER`; pilot count invalidated at game 1.
- **evidence:** The first matched game was incomplete-information, unknown-horizon,
  buyer role against disclosed agent `OpenProgram`. ROBUST repeatedly countered 60 while
  the opponent repeatedly countered 156. With no mechanism horizon, neither policy had a
  terminal condition and the bounded family run could consume its overall deadline.
- **action taken:** Queueing was stopped. The already-active game was ended with the
  predefined advertised `WalkAway` legal fallback; the server accepted it and post-drain
  state was zero active and zero pending. No second game was queued. The aborted transcript
  is retained as `research/evaluation/pilot_negotiation_aborted_023d8f4.jsonl`.
  A generic pilot-layer no-progress detector now treats three consecutive identical
  observed-offer/economic-response pairs in unknown-horizon bargaining or negotiation as
  a hard stop, substitutes the advertised legal fallback, and drains without requeueing.
  Changed offers reset the count; finite games and persuasion are unaffected. The full
  negotiation pilot must restart from zero on the new frozen commit.

## Stopped second MVL negotiation pilot — emergency guard exercised

- **item:** Restarted frozen negotiation pilot on commit
  `be442310dbd89aac65b8ec459cd4e76614801846`.
- **result:** `CONTRADICTED` — hard stop at 2/10; qualification count invalidated.
- **evidence:** Game 1 was incomplete finite-horizon buyer ROBUST and ended no-deal with
  payoff 0. Game 2 was incomplete unknown-horizon seller ROBUST. The opponent improved
  from 996000 toward 1199999.99, then repeated 1199999.99 while ROBUST repeated 1800000.
  On the third identical plateau pair, the pilot safety layer selected the advertised
  `WalkAway`; the action was valid, the game ended at (0,0), the supervisor returned
  `STOP_REQUESTED`, and postflight was zero active/zero pending.
- **action taken:** Because the emergency pilot backstop was invoked, the family is not
  ready and the transcript is retained as
  `research/evaluation/pilot_negotiation_aborted_be44231.jsonl`. The same generic rule is
  now inside each relevant named incumbent: negotiation ROBUST and both unknown-horizon
  bargaining paths choose walk-away on the third identical rejected pair. Offline replay
  of the exact live terminal state selects ROBUST `WalkAway` with no execution fallback.
  The independent pilot guard remains only as a hard-stop backstop. The negotiation pilot
  must restart from zero on the next frozen commit.

## Qualifying frozen MVL pilots

- **item:** Frozen family qualification on
  `49a6021726553425506a09e23798b813c6091d9a` after all deployment blockers were closed.
- **result:** `CONFIRMED`
- **evidence:** Negotiation completed 10/10, bargaining 3/3, and persuasion 3/3. Every
  family returned `MAX_GAMES_COMPLETED`; the same frozen policy commit produced all 16
  games. Across the qualifying transcripts there were zero invalid moves, hard-stop
  events, `UNSUPPORTED_CELL` routes, policy-execution fallbacks, outer never-raise
  fallbacks, emergency pilot actions, or strategic-review events. Maximum live local
  policy latencies were 3.6666 ms negotiation, 2.1858 ms bargaining, and 3.4058 ms
  persuasion. Final cleanup was explicitly repeated after all pilots and returned
  `active_games=0`, `pending_games=0`.
- **outcomes:** Negotiation rating 982.37 -> 974.79; bargaining 1680.69 -> 1670.46;
  persuasion 1403.77 -> 1402.31. Rating increase was not a readiness criterion. Exact
  game/action/payoff and per-cell/role results are in the three
  `docs/pilot_*_report.md` files and corresponding JSONL transcripts.
- **status:** `NEGOTIATION_MVL_READY=yes`, `BARGAINING_MVL_READY=yes`,
  `PERSUASION_MVL_READY=yes`, `ALL_FAMILIES_MVL_READY=yes`.
- **classification:** No remaining `DEPLOYMENT_BLOCKER`. The incomplete advanced policies
  listed in the experiment registry remain `RESEARCH_BLOCKED`.
- **action taken:** All queues are stopped. No sustained or additional rated execution
  was started; scaling requires explicit human approval.

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
  to `.04S` raw utility. The full suite passes 69 tests, and the third controlled canary
  verified live execution without any missing-price-bound fallback.

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
  started. Live ROBUST *routing* was verified; at that point action execution remained
  blocked pending an authorized formulation compatible with an unbounded price domain.
  That historical blocker is resolved by the policy redesign and third canary below.

## Third controlled rated canary — unbounded-domain ROBUST execution

- **item:** Exactly one post-redesign negotiation canary validating normal ROBUST
  execution, payoff transformation, and automatic bounded completion.
- **source inspected:** Structured state/route/ROBUST/action/supervisor stream and
  terminal `game_state()` for game `10df5ea0-5290-4ba1-b8c1-8544aacde6ba` on 2026-08-21.
- **result:** `CONFIRMED`
- **evidence:** Preflight returned `active_games=0` and no pending games. The match was
  incomplete-information negotiation, known finite horizon `T=10`, messages disabled;
  our role was buyer (`player_2`) with private value `V_B=8000`, against disclosed agent
  `champion`. BAYES eligibility/artifacts were unavailable, so the route selected
  `NEGOTIATION_ROBUST` with no execution fallback. The buyer policy candidates were
  `[0,2000,4000,6000,8000]` and seller-value scenarios were the same. Maximum regrets by
  candidate were respectively `[6000,4000,4000,6000,8000]`; the fixed higher-buyer-offer
  tie-break selected 4000 over 2000. The seller offered 14290, 8426.56, 8415.04, 8403.52,
  and 8392 on our five decision turns. Every offer exceeded `V_B` and was non-IR, so each
  deterministic response was `RejectOffer` with a 4000 counteroffer. All five actions
  were valid. The seller rejected the round-10 offer and the terminal outcome was
  `no_deal`, with both payoffs zero.
- **dependent components:** Policy-generated action/scenario grids, regret diagnostics,
  current-offer response rule, routing, clipped payoff transform, and bounded supervisor.
- **action taken:** Raw own payoff `U=0` with `S=8000` gave `C=16000` and transformed
  `Y=.5`; clipping did not occur. Policy-execution and outer never-raise fallback counts
  were both zero. `run_bounded(max_games=1, concurrency=1, requeue=False)` made one queue
  call, returned automatically with `MAX_GAMES_COMPLETED` after 20.99 seconds, and cleaned
  the queue. Postflight returned `active_games=0`, no pending games, and negotiation games
  played increased from 109 to 110. No second game, experiment, or persistent execution
  was started.

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

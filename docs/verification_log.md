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

## 2. Negotiation legal price bounds

- **item:** Finite live legal price range and whether accepted trades can yield negative
  utility.
- **source inspected:** Official `glee-sdk` v0.0.5 source and README; GLEE reference
  validator `games/negotiation/negotiation.py`; controlled live rated negotiation canary
  `ba9c3e41-8b3a-4e77-8d81-d5b01abf17a7` on 2026-08-21.
- **result:** `BLOCKED`
- **evidence:** SDK `valid_actions.fields` documents `product_price` only as `number`; it
  supplies no finite minimum/maximum. The historical validator accepts numeric values but
  is not authoritative for the current live competition. In the live incomplete-info,
  unlimited-horizon seller state, `valid_actions` was exactly
  `{"type":"offer","fields":{"message":"string (optional message)",
  "product_price":"number (your proposed price)"}}`. The visible game state exposed no
  `p_min`, `p_max`, `M`, price grid, product-price scale, or other finite-bound metadata.
  The legal action `product_price=10000.0` was accepted by the server, but one accepted
  price establishes neither endpoint.
- **dependent components:** Negotiation payoff-bound instantiation in
  `glee/normalization.py` and any live legal-price grid construction.
- **action taken:** No bound is fabricated. `glee/normalization.py` remains unchanged and
  continues to require explicit verified finite bounds. Resolving this item still requires
  authoritative validator/config documentation or a live payload that exposes endpoints;
  probing arbitrary prices in rated games is not used as a discovery method.

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
  its `finally` block left the queue. This behavior must be handled before reusing
  `run(requeue=False)` as an unattended bounded runner.

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

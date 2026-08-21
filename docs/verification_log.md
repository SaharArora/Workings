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
  validator `games/negotiation/negotiation.py`.
- **result:** `BLOCKED`
- **evidence:** SDK `valid_actions.fields` documents `product_price` only as `number`; it
  supplies no finite minimum/maximum. The historical validator accepts numeric values but
  is not authoritative for the current live competition. No `GLEE_API_KEY` is present to
  inspect a live assigned game's `valid_actions` payload.
- **dependent components:** Negotiation payoff-bound instantiation in
  `glee/normalization.py` and any live legal-price grid construction.
- **action taken:** No bound is fabricated. Generic normalization will require explicit,
  verified bounds and the live instantiation remains blocked.

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
- **source inspected:** Host environment and adapter integration tests.
- **result:** `BLOCKED`
- **evidence:** `GLEE_API_KEY` is absent from the execution environment. The previously
  committed example credential was exposed and is intentionally not reused.
- **dependent components:** Completion criterion for live API smoke testing.
- **action taken:** Adapter is tested with an injected SDK fake; live smoke remains
  required after a rotated credential is supplied securely.

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
- **source inspected:** Host credential environment and experiment registry.
- **result:** `BLOCKED`
- **evidence:** No rotated `GLEE_API_KEY` is present, no live games were queued, and the
  registry contains no completed randomized experiment.
- **dependent components:** Empirical promotions, same-cell confirmation, active
  non-default policy map, and real leaderboard deployment claims.
- **action taken:** Implemented the auditable harness and retained default incumbents;
  no candidate is represented as promoted.

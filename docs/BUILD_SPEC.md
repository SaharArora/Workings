# GLEE Agent + Research System — Build Specification

## Repository and execution context

### Target repository

- GitHub URL: `https://github.com/SaharArora/Workings`
- Full name: `SaharArora/Workings`
- Default branch: `main`
- The repository is public and currently empty (reported size 0). Build this system in
  that repository from scratch. If any existing file is discovered at execution time, do
  not delete or overwrite it without first reporting what was found — do not assume the
  repository is empty without checking.

### Runtime

- Python: 3.12
- Package manager: `uv`, with a standard `pyproject.toml`
- Test framework: `pytest`
- GLEE API credential: read from environment variable `GLEE_API_KEY` (not
  `GLEE_API_TOKEN` — corrected per the SDK README). Never commit
  credentials. Provide a `.env.example` listing variable names only (no values); `.env`
  itself must be in `.gitignore`.
- **Transport**: the official SDK reportedly exposes `glee_sdk.GleeClient`, with a
  `client.run(strategy, ...)` method already handling queueing, polling, dispatch,
  concurrency, draining, retries, and rate limiting for all three families through one
  loop. **This specific package name, class name, and method signature have not been
  independently verified by inspecting the SDK directly in this spec's own research
  process** — they are relayed from external SDK documentation, not confirmed against
  primary source the way the game-mechanics facts in §3 were. Treat this as a
  **VERIFY-FIRST item**: confirm the actual installed package's exact interface before
  building `glee/client.py` around it. If confirmed, `glee/client.py` becomes a thin
  adapter around `glee_sdk.GleeClient` — normalizing payloads into our internal schemas,
  configuring family/concurrency, wrapping safe fallbacks, collecting telemetry — and
  does not reimplement HTTP/retry/rate-limit mechanics the SDK already owns. If the
  actual installed SDK does not match this description, fall back to the originally
  specified custom `glee/client.py` + `glee/retry.py` implementation (§2) rather than
  blocking on this mismatch.
- **Historical GLEE dataset source**: public repository `https://github.com/eilamshapira/GLEE`,
  branch `master`, directory `Data/`. This is a confirmed, real public source — not
  fabricated. **Do not do a full upfront ingest of this dataset, and do not leave every
  data-dependent component BLOCKED by default either.** Use a targeted-first strategy:
  1. Inspect the actual `Data/` directory structure directly (its exact internal layout —
     e.g. whether it splits by `human_vs_llm`/`llm_vs_llm`, whether individual games are
     stored as per-cell folders with something like `config.json`/`game.csv`, or some
     other structure — has **not** been independently verified as of this spec and must
     be confirmed by direct inspection, not assumed).
  2. Identify negotiation configuration cells first (these are what §5.2's BAYES
     eligibility check and the underdetermined-cell candidate portfolio in §5.1 need).
  3. Ingest only those cells initially; count games per cell.
  4. Check which cells reach the `n≥200` eligibility threshold (§5.2).
  5. Profile file count, total bytes, and parse time for this targeted subset before
     deciding whether to expand further.
  6. Expand to bargaining/persuasion cells, or the full corpus, only if the profiling in
     step 5 shows it is cheap relative to the remaining build time — this is a judgment
     call to make with the actual profiling numbers in hand, not a default either way.

  Mark a data-dependent component BLOCKED only if the specific cell(s) it needs remain
  unavailable or under-supported after this process — not merely because the full corpus
  has not been ingested. The ingestion layer (`data/`, feeding `research/`) must be
  written so additional cells/families can be added incrementally later without a
  redesign.
- **GLEE reference implementation**: `https://github.com/eilamshapira/GLEE` also contains
  the original research-code implementation (`players/`, `games/`, `http_player/`,
  `interface.py`, `sample_configs/`). Use this as a **mechanism-reference source** for
  game logic and historical-data schemas when resolving VERIFY-FIRST items (§10) — but
  do not assume its historical implementation is identical to the current live
  competition API. The competition API/docs already reproduced in §3 remain authoritative
  for live request/response behavior. Log any mismatch discovered between the two under
  VERIFY-FIRST in `docs/verification_log.md`, per the top-of-document protocol — do not
  silently prefer one source over the other.

### Git workflow

- `main` is the only long-lived branch, per §2.
- Work on short-lived implementation branches; merge to `main` only after that branch's
  tests pass. Do not commit directly to `main` without tests passing first.

### Completion criteria (what "done" means for this build)

- Full repository structure created per §2.
- VERIFY-FIRST items (§10) attempted and their outcomes — confirmed, contradicted, or
  blocked pending missing input — logged in `docs/verification_log.md`.
- Unit tests passing for every theory baseline (§4) against hand-computed cases.
- `eprocess/betting.py` passing deterministic synthetic tests (known input sequence,
  known expected `E_t` trajectory), including the required synthetic-null validity test
  from §6.2.
- `glee/client.py` passing a safe smoke test against the real API (queue, poll,
  leave-queue; no live game moves required for this smoke test).
- Every component that depends on the historical dataset or the SDK source, where those
  remain unsupplied or a specific cell's data is unavailable, is explicitly marked
  BLOCKED rather than silently skipped or faked — this is a required, visible part of
  "done," not a failure.

## 0. How to use this document

This is a complete build specification, not a brainstorm. It is the output of an extended
design process that resolved architecture, theory, and statistics questions one at a time.
Treat every decision below as final unless explicitly marked **VERIFY-FIRST**.

**Implement the specification as written. Do not substitute alternative statistical
procedures, theoretical baselines, thresholds, normalization rules, policy definitions, or
directory structures because another method appears preferable, more standard, or more
elegant.** Every threshold, formula, and structural choice below was deliberately chosen —
often after rejecting a more sophisticated alternative in favor of simplicity — and is not
open for silent revision.

Two categories of statement appear below:

- **Specified facts.** Game mechanics, formulas, architecture, and procedures. Implement
  exactly as written.
- **VERIFY-FIRST items.** Marked explicitly wherever they appear. These are assumptions
  about the real GLEE mechanism that must be checked against the authoritative GLEE
  paper/SDK/API before any code that depends on them is written. If what you find
  contradicts the assumption stated here, **stop that dependent implementation, document
  the discrepancy in `docs/verification_log.md`, and surface it for review rather than
  inventing a workaround or silently adapting the spec.**

Some numeric choices below (`n≥200`, `BSS≥0.10`, `ECE`/calibration procedure, `α=0.05`,
the four-λ betting mixture, `M` per cell) are **deliberately chosen v1 defaults**, not
mathematical truths. Implement them exactly as given, and expose every one of them as
named configuration constants (not hardcoded literals) so they can be revisited later
without a code change — but do not tune them now.

---

## 1. Project objective

Build **two separate agents** sharing common infrastructure:

1. **Leaderboard agent** (`leaderboard/`) — the production competition entry. Uses the
   full architecture including a language/communication component. Optimizes for actual
   competition performance. Not held to the same measurement discipline as the research
   agent on its language component, because language effects are not measurable by the
   offline evaluation harness (see §6).

2. **Research agent** (`research/`) — used to produce one clean, fully-measurable
   scientific result: does evidence-gated population-level policy adaptation
   (`Δ_population`, governed by an anytime-valid e-process) outperform a pure
   theory-plus-instance-adaptation baseline, with no language component at all. This is a
   **single before/after comparison**, not a four-arm study. The two agents being
   compared are:
   - **IBO** (Individual Bayesian Optimizer) = `π_theory(C) + Δ_instance(h_t)` — the baseline.
   - **EG-SPM** (Evidence-Gated Strategic Population Model) = `π_theory(C) + Δ_population(C,τ) + Δ_instance(h_t)` — the full research system.

   Neither research variant includes `Δ_communication`. Both may still *read* incoming
   opponent text for belief-updating within `Δ_instance` (this is not "language strategy,"
   it is using an available observation the same way offers/rejections are used). Neither
   *generates* optimized or adaptive language. Where the protocol requires a message
   field, both send a fixed, non-strategic placeholder string, identical for both agents,
   defined once in `communication/neutral.py`.

The overall system formula (leaderboard agent, full form):

```
π_t = π_theory(C) + Δ_population(C, τ) + Δ_instance(h_t) + Δ_communication(m_t, h_t, τ)
```

Where:
- `C` — the exact game configuration (information structure, horizon, communication mode, role, etc. — see §4).
- `τ` — opponent type/category, disclosed (`human`/`agent`) or `hidden`, per the API.
- `π_theory(C)` — configuration-specific theoretical baseline. Depends only on `C`, never
  on opponent identity. See §4 for the full per-game table.
- `Δ_population(C, τ)` — an empirically-motivated deviation from theory, active only if
  promoted by the e-process for that (cell, opponent-category) pair. See §5–§8.
- `Δ_instance(h_t)` — ordinary Bayesian belief-updating from the current game's observed
  history (opponent offers, rejections, messages). Never switches which policy family is
  active; only adjusts parameters (e.g., a re-estimated valuation) within whatever policy
  is currently active. See §5.3 for the explicit boundary rules that keep this from
  regressing into a heuristic mode-switching system.
- `Δ_communication(m_t, h_t, τ)` — leaderboard-agent-only strategic language generation.
  Absent entirely from the research agent. **Hard constraint**: `Δ_communication` may
  choose *how* to express the numeric action already decided by
  `π_theory + Δ_population + Δ_instance` — it must never silently change *what* that
  action is. The economic decision is finalized before language generation runs; language
  generation renders it, it does not revise it.

**Leaderboard runtime architecture**: one process, one dispatcher, all three families —
not separate processes per family. `leaderboard/agent.py` wraps a single strategy
callback dispatched through the transport (§3.4/§10's VERIFY-FIRST item), with
`policy_router.py` doing the actual per-arriving-game routing: inspect the game's family
and configuration cell, inspect disclosed opponent category (or `hidden`), route to that
`(cell, τ)`'s current policy per the policy map (§7.2), execute it (including
`Δ_instance` per §5.3), attach communication if this is the leaderboard agent.

**Queueing strategy note**: the overall leaderboard score is the **equal-weight average**
of the three per-family ratings, and an unplayed family counts at the 1,000 starting
rating (confirmed directly in the rules documentation already reproduced in this spec).
This means queueing only one family indefinitely, however well that family is played,
leaves the other two families dragging the overall average down at the 1,000 floor —
worth keeping in mind when configuring which families the leaderboard agent actually
queues for; this spec does not mandate a specific queueing split, but flags that
single-family-only queueing has this real cost unless deliberately chosen.

---

## 2. Repository structure (locked)

```
repo/
├── leaderboard/
│   ├── agent.py
│   ├── policy_router.py
│   └── config.py
│
├── research/
│   ├── experiments/
│   │   ├── economic/        # must NOT import communication/
│   │   │   ├── bargaining/
│   │   │   ├── negotiation/
│   │   │   └── persuasion/
│   │   └── communication/   # may import communication/ — language IS the treatment here
│   ├── training/             # fits BAYES/EMPIRICAL models; see §5.1
│   │   └── negotiation/
│   │       ├── train_bayes_response.py
│   │       └── train_empirical_response.py
│   ├── analysis/
│   └── evaluation/
│
├── theory/
│   ├── bargaining/
│   ├── negotiation/
│   └── persuasion/
│
├── policies/
│   ├── bargaining/
│   │   ├── theory.py
│   │   └── fairness.py
│   ├── negotiation/
│   │   ├── theory.py
│   │   ├── bayes.py
│   │   ├── robust.py
│   │   ├── empirical.py
│   │   ├── fairness_margin.py       # §4.2 deviation, complete-info cells
│   │   ├── anchor_favorable.py      # §4.2 deviation, unbounded-horizon complete-info
│   │   └── empirical_correction.py  # §4.2 deviation, incomplete-info T=1 cells
│   └── persuasion/
│       ├── babbling.py
│       └── reputation.py
│
├── opponent_models/
│
├── communication/
│   ├── neutral.py            # fixed non-strategic placeholder used by research agent
│   └── strategic.py          # leaderboard-agent-only
│
├── eprocess/
│   ├── betting.py            # pure math primitive, knows nothing about GLEE
│   └── experiment.py         # experimental wrapper: cell, incumbent, candidate, alpha, M, observations
│
├── glee/
│   ├── client.py              # thin adapter around glee_sdk.GleeClient (VERIFY-FIRST,
│   │                          # §10) if confirmed, else owns HTTP/API semantics directly
│   ├── schemas.py
│   ├── retry.py                # strategy-output validation/fallback retry only (the
│   │                           # never-raise wrapper, §3.4) — not network-level retry,
│   │                           # which is the SDK transport's job where confirmed.
│   └── normalization.py       # generic mechanism-derived Y-normalization (§9)
│
├── data/
│   ├── README.md               # acquisition/location of the historical GLEE dataset; do not commit raw data
│   ├── processed/
│   │   └── models/             # frozen trained BAYES/EMPIRICAL artifacts, versioned; §5.1
│   │       └── negotiation/
│   │           └── <cell>/<opponent_category>/<version>/
│   └── schemas/
│
├── scripts/
│   ├── run_leaderboard.py
│   ├── run_experiment.py
│   └── evaluate.py
│
├── tests/
│   ├── theory/
│   ├── policies/
│   ├── eprocess/
│   └── integration/
│
├── docs/
│   ├── architecture.md
│   ├── theory_baselines.md
│   ├── experiment_registry.md
│   └── verification_log.md     # VERIFY-FIRST findings go here
│
├── pyproject.toml
├── README.md
└── .gitignore
```

Repository constraints:

- `main` is the only long-lived branch. Short-lived work branches are acceptable only if
  the execution environment requires them; merge/delete immediately.
- No scratch scripts in repo root. No `foo_test.py`, `analysis2.py`, temporary notebooks,
  downloaded datasets, generated outputs, or one-off experiments outside their designated
  folders. `scripts/` contains maintained, sanctioned recurring entry points only —
  one-off analyses belong under `research/`, never in `scripts/` or repo root.
- Raw large GLEE data is not committed to git. `data/README.md` describes acquisition and
  location; schemas and small fixtures may be committed.
- Every theoretical baseline (`theory/`) needs a unit test against a hand-computed case.
- Every new policy needs an entry in `docs/experiment_registry.md` before it becomes
  leaderboard-eligible.
- `research/` must not silently affect `leaderboard/`. A policy is promoted into
  `leaderboard/` only by deliberate, documented action referencing an experiment-registry
  entry — never automatically.
- Within `research/experiments/`: `economic/` experiments must not import or invoke
  `communication/` — they use `communication/neutral.py` only, so the economic policy's
  effect can never be confounded with language. `communication/` experiments may
  explicitly import `communication/`, since language is the deliberate treatment under
  study there.
- `leaderboard/` must remain runnable independently of exploratory notebooks or
  unversioned artifacts.
- `theory/` contains only configuration-specific theoretical baselines — no learned
  behavioral corrections. If real players behave differently from theory, that belongs in
  `policies/` or `opponent_models/`, never in `theory/`.

---

## 3. GLEE mechanics reference

Source of truth: the GLEE paper (Shapira et al., "GLEE: A Unified Framework and Benchmark
for Language-based Economic Environments," arXiv:2410.05254) and the competition SDK/API
docs. Do not rely on memory or secondary summaries for anything not restated explicitly
below — re-derive from source if in doubt.

### 3.1 Bargaining ("Divide the Dollar")

- Players Alice (player 1) and Bob (player 2) alternate proposing a split of a fixed sum
  `M`. Alice proposes on odd stages, Bob on even stages.
- Per-round discount multipliers `δ_A`, `δ_B` apply — real, per-player, confirmed in the
  primary source. If proposal accepted at stage `t` with Alice's share `p`:
  `u_A = M · δ_A^(t-1) · p`, `u_B = M · δ_B^(t-1) · (1-p)`.
- No agreement by `max_rounds` (if capped) → both get 0. Uncapped games have no
  `max_rounds` field (`horizon_known: false`).
- A `walkaway` action ends the game immediately at (0,0), available at every decision point.
- Config axes: complete/incomplete info (opponent's δ hidden or known), finite/unbounded
  horizon, messages allowed/not, values of `δ_A`, `δ_B`, `M`, `T`.

### 3.2 Negotiation ("Bilateral Trade")

- Seller (Alice, player 1, has reservation value `V_A`) and buyer (Bob, player 2, has
  valuation `V_B`) alternate price offers. Alice proposes odd stages, Bob even stages.
- **No discounting** — confirmed explicitly in the primary source as the key structural
  difference from bargaining. If price `p` accepted: `u_A = p − V_A`, `u_B = V_B − p`. No
  trade → both get 0.
- `WalkAway` action ends the game immediately at (0,0).
- Horizons: `T ∈ {1, 10, ∞}` are the values actually used in GLEE's own data collection
  (confirmed in the primary source's parameterization table) — `T=1` is single-round
  take-it-or-leave-it (no counteroffer exists), `T=10` is a real, commonly-used finite
  cap, `∞` means large-and-unknown to both players (`horizon_known: false`).
- Config axes: complete/incomplete info (opponent's valuation hidden or known), horizon,
  messages allowed/not, values of `F_A`, `F_B` (valuation scale factors), `M`.

### 3.3 Persuasion ("Strategic Information Transmission")

- Seller (Alice) knows each round's true product quality (`high`/`low`); buyer (Bob)
  knows only the prior `p = P(quality=high)`.
- Fixed price, normalized: price `= 1`, low-quality value `u = 0`, high-quality value `v`.
  Buyer utility from purchase: `M(v−1)` if high quality, `−M` if low quality, `0` if no
  purchase. Seller earns the price on every sale regardless of quality.
- Communication mode: `binary` (recommend yes/no) or `textual` (free message) — a real,
  confirmed config axis.
- Seller may or may not know buyer's `v` (the `is_seller_know_cv`-style toggle) —
  confirmed real via the primary source ("the seller may or may not know the buyer's
  values depending on the information configuration").
- **Correction from an earlier version of this spec**: the underlying GLEE research
  paper/environment describes a `long-living` vs. `myopic` buyer axis (myopic buyers see
  only summary statistics rather than full history). **The live competition's own rules
  documentation states plainly that "the buyer remembers the whole interaction," and the
  live `game_state` schema for persuasion (§3.3's field list above) has no `buyer_type` or
  equivalent field.** This is independently confirmed directly from documentation already
  reproduced in this spec's own research, not merely relayed secondhand. Treat the
  myopic/long-living axis as **not present in the live competition** — every live buyer is
  history-aware. Do not build cell definitions, policy routing, or population strata
  around a myopic/long-living split. If direct inspection of the SDK or live payloads ever
  reveals otherwise, log the discrepancy in `docs/verification_log.md` and revisit — but do
  not assume it exists by default.
- **Quality feedback is censored by purchase**: the buyer learns a given round's actual
  realized quality only if they bought that round (`history[i].quality` is present only
  when `history[i].bought` is true) — confirmed directly from the rules documentation
  already reproduced in this spec. The seller always sees the true quality regardless.
  Any policy or belief-update logic reasoning about "what the buyer knows" must respect
  this censoring — do not assume the buyer's model has access to quality on rounds they
  didn't purchase.
- Game runs a known, fixed number of rounds `T`; payoffs sum across rounds.

### 3.4 API mechanics (all three games)

- Base URL `https://glee-competition.com`. Bearer-token auth. Rate limit 60 req/min per
  agent (429 + `Retry-After` on excess). **Network/API-level retry and backoff is the
  SDK transport's responsibility (see "Repository and execution context" for the
  VERIFY-FIRST caveat on the exact SDK interface) — do not duplicate that logic in our
  own code.** Our code's responsibility is strategy-output validation and fallback only
  (see the never-raise wrapper below), a distinct layer from network retry.
- Matchmaking: queue per **game family** (`bargaining`/`negotiation`/`persuasion`), not
  per specific configuration cell. **You do not choose which config cell you play, and
  you cannot deploy "into" a specific cell — the server assigns the cell for each
  arriving game.** This has an architectural consequence beyond just constraining
  experiment allocation: see §7.2's revision — there is no "choose the final cell to
  deploy into" decision to make, because that decision was never ours to make. Only
  "which policy is currently active for whichever cell arrives" is under our control.
- `opponent` field: disclosed (`{type: "human"|"agent", name: str}`) in a random half of
  games, `{type: "hidden", name: null}` in the other half. **Correction to an earlier
  overconfident version of this spec**: `"agent"` and `"hidden"` are confirmed as literal
  enum values via actual JSON examples already reproduced in this spec's own research; the
  string `"human"` is described only in prose ("a human, another participant's agent, or
  an LLM baseline") and was never confirmed as the literal JSON value via a shown example.
  Treat `τ ∈ {human, agent, hidden}` as the working assumption, with the literal string for
  the human case as a **light residual VERIFY-FIRST item** (§10) — cheap to confirm from
  one real disclosed-human game payload, not the larger unknown it was originally treated
  as before "agent"/"hidden" were confirmed.
- **`valid_actions["type"]` and `valid_actions["fields"]`, as returned per pending game,
  are authoritative for legal-action construction and validation at every turn** — do
  not hardcode action shapes purely from the family-level schemas in §3.1–3.3 without
  also checking the live `valid_actions` payload, since it reflects turn-specific legality
  (e.g. a negotiation final round permits `{"decision": "RejectOffer"}` with no
  counteroffer, which the general family schema alone would not tell you).
- Message length: any move carrying a message allows unrestricted strategic text up to a
  **2,000-character hard limit** — a longer message is rejected as an invalid move and
  costs one of the 5 attempts. Both `communication/neutral.py` and
  `communication/strategic.py` must enforce this, and should target a lower internal
  ceiling (e.g. 1,500–1,800 characters) to leave margin rather than writing right up to
  the hard limit.
- 5 move attempts per game before auto-no-deal on the 5th failure; 120 seconds per turn
  before auto-no-deal. All agent code must always emit a syntactically legal move within
  budget. Implement a never-raise wrapper around every move-generating call path: catch
  every exception at the outermost decision-making boundary, and on any failure fall back
  to a predefined, always-legal default action for that game/phase (e.g., the cheapest
  safe response the current `valid_actions` schema allows) rather than letting an
  exception propagate and cost a move attempt or the whole game. This wrapper handles
  *our own* logic failures — it is a different concern from the SDK's network-level retry
  noted above, and both are required, not one substituting for the other.
- No access to the historical ~1M-game dataset through this API. Population-level offline
  estimation (`Δ_population` construction, `π_EMPIRICAL`, eligibility checks, priority
  scores) draws from the separately-acquired historical GLEE dataset (see `data/README.md`),
  not from this live API.

---

## 4. Theoretical baselines (`π_theory(C)`) — locked, per game, per configuration cell

`theory/` implements exactly this table. No cell gets a baseline not listed here without
new design work.

### 4.1 Bargaining

| Info | Horizon | `π_theory(C)` |
|---|---|---|
| Complete | Unlimited/unknown | Rubinstein stationary SPE: Alice's share `x*_A = (1−δ_B)/(1−δ_Aδ_B)` |
| Complete | Finite, known `T` | Exact backward induction, alternating roles. Let `A_prop(r)` = Alice's share when *she* proposes with `r` rounds remaining (including the current round); `B_prop(r)` = Bob's share when *he* proposes with `r` rounds remaining. Base case (`r=1`, last round): whoever proposes gets everything — `A_prop(1) = B_prop(1) = 1`. Recursive step (`r≥2`): `A_prop(r) = 1 − δ_B · B_prop(r−1)`, `B_prop(r) = 1 − δ_A · A_prop(r−1)` (the responder is indifferent between accepting now and rejecting to become proposer next round, discounted one step by their own δ). Compute from `r=1` up to `r=T`; the round-1 offer (immediate agreement under complete information) is `A_prop(T)` if Alice proposes first. This recursion is internally consistent with the infinite-horizon Rubinstein formula above: as `r→∞` it converges to the same fixed point `A* = (1−δ_B)/(1−δ_Aδ_B)`. Implement both `A_prop` and `B_prop` explicitly as two interleaved sequences — do not collapse this into a single scalar recursion that ignores which player is proposing at each step. |
| Incomplete | Finite | Bayesian dynamic program / type-screening approximation, integrating over a discrete prior `P(δ_{-i})` — explicitly a **Bayes-adaptive approximation**, not a claimed exact perfect Bayesian equilibrium. (Note: this integrates over the full posterior rather than plugging in a single point estimate of `δ_{-i}`, so it is not a certainty-equivalent method in the technical sense — do not use that term for this row.) |
| Incomplete | Unlimited/unknown | Bayes-adaptive bargaining using Rubinstein continuation values as type-conditioned reference points — same approximation caveat |

**Locked deviation `B` for bargaining — applies uniformly to all four cells above.**
`policies/bargaining/fairness.py` implements a single deviation, tested against that
cell's own `π_theory(C)` as incumbent `A` (whichever of the four rows above applies —
exact SPE, exact backward induction, or one of the two Bayes-adaptive approximations; the
deviation always operates on top of whatever `A` computed for that round, it does not
re-derive equilibrium from scratch). This operationalizes Fehr–Schmidt-style
inequity-aversion as a simple, implementable concession rule — **not** a full re-solved
Fehr–Schmidt equilibrium, which would be a materially larger undertaking than v1 needs:

```
x_theory = the proposer's share as computed by π_theory(C) for this round
δ_fair   = 0.10          (v1 default concession fraction — a deliberately chosen
                          starting value, not derived from a specific published
                          Fehr–Schmidt parameter estimate; revisit only with
                          evidence, per this spec's general default-handling rule)

x_dev = x_theory − δ_fair · (x_theory − 0.5)
```

i.e., the deviation concedes 10% of the theoretical offer's distance from an even split,
in the direction of fairness, and proposes `x_dev` instead of `x_theory`. This is
deliberately simple and auditable rather than a full behavioral-game-theory
reconstruction. Rationale for testing this at all: GLEE's own data shows full theoretical
extraction can *reduce* efficiency, because a responder who perceives an offer as unfair
may reject it even when accepting is individually rational — this deviation is the
concrete, testable hypothesis that conceding a bounded amount recovers some of that lost
efficiency without giving up too much on realized splits.

### 4.2 Negotiation

| Info | Horizon | `π_theory(C)` |
|---|---|---|
| Complete | `T=1` | Alice offers `p* = V_B` (full extraction subject to indifference tie-break); Bob accepts iff `p ≤ V_B` |
| Complete | Finite, odd `T` | Seller is terminal proposer → canonical `p* = V_B` at every on-path proposal (seller captures all gains-from-trade `S = V_B − V_A`) |
| Complete | Finite, even `T` | Buyer is terminal proposer → canonical `p* = V_A` (buyer captures all `S`). **VERIFY-FIRST**: confirm real games at `max_rounds=10` (an even value actually used per §3.2) place Bob as terminal proposer under the actual API's round/proposer numbering — spot-check ~20-30 real logged games; if Alice is proposer at the terminal round instead, stop and report the discrepancy rather than assuming parity. |
| Complete | Unlimited/unknown | **No unique baseline in theory** — a continuum of efficient equilibria on `p* ∈ [V_A, V_B]`. `π_theory(C)` for this cell is **operationally fixed to the midpoint** `p* = (V_A + V_B)/2` as the deployed convention (a real number must be output even though theory doesn't privilege one point) — see the locked deviation below for the tested alternative. Do not report a single-point regret against this cell in evaluation; report efficiency (trade occurred iff it should have) separately from the distributional question. |
| Incomplete + trusted prior | `T=1` | Bayes-optimal posted price: `p* = argmax_{p≥V_A} (p−V_A)[1−F_B(p)]` |
| Incomplete + ambiguous/no prior | `T=1` | Robust/minimax-regret randomized pricing (Bergemann & Schlag) |
| Incomplete | Multi-round or unlimited | **No clean closed form.** Use the locked three-policy portfolio in §5 as candidate deviations from a chosen default incumbent (§5.2). |

First-order decomposition, applies to every negotiation cell before anything else: if
`V_B < V_A`, no individually rational price exists — theoretical outcome is no trade,
efficient outcome is `(0,0)`. Implement this check first, unconditionally.

**Locked deviations `B` for negotiation's six determined cells** (the seventh row — the
underdetermined cell — is handled separately in §5, including its own incumbent-selection
rule; do not apply anything below to that cell).

*Complete-information cells (`T=1`, finite odd, finite even) — one shared deviation,
`policies/negotiation/fairness_margin.py`.* In each of these three cells, `π_theory(C)`
gives one side the *entire* gains-from-trade `S = V_B − V_A` (full extraction). The
deviation concedes a fixed fraction of `S` to the counterpart instead:

```
S = V_B − V_A
β = 0.15    (v1 default concession fraction — chosen default, not derived; same
             treatment as δ_fair above and every other v1 constant in this spec)

If π_theory(C) gives the seller p* = V_B (T=1, finite-odd rows):
    p_dev = V_B − β·S     (seller concedes β·S of the surplus to the buyer)

If π_theory(C) gives the buyer the full surplus (finite-even row, p* = V_A):
    p_dev = V_A + β·S     (buyer concedes β·S of the surplus to the seller)
```

Rationale: identical to bargaining's fairness deviation above — a fully extractive offer
risks rejection from a counterpart who perceives it as unfair even when accepting is
individually rational; this tests whether a bounded, fixed concession recovers trade
efficiency lost to that behavior.

*Complete-information, unlimited/unknown horizon — `policies/negotiation/anchor_favorable.py`.*
Since `π_theory(C)` here is only an operational convention (the midpoint, per the table
above), not a privileged equilibrium point, the deviation tests a different, equally
theory-legitimate point in the same continuum:

```
γ = 0.65    (v1 default — proposer's own-favorable share of S, vs. the 0.5 implied
             by the midpoint convention; chosen default, not derived)

p_dev = V_A + γ·S     if the agent's own role is seller
p_dev = V_A + (1−γ)·S if the agent's own role is buyer
```

This is a genuine, well-posed empirical question precisely *because* theory is silent on
which point in `[V_A, V_B]` is correct — both the midpoint and the own-favorable anchor
are equally defensible game-theoretically, so which one performs better against real
opponents is exactly the kind of question the e-process framework exists to answer.

*Incomplete-information, `T=1` (both the trusted-prior and ambiguous-prior rows) — one
shared deviation, `policies/negotiation/empirical_correction.py`.* Both rows' theoretical
prices are computed from an assumed belief about the counterpart's valuation (`F_B` for
the trusted-prior row, the ambiguity set for the robust-pricing row). The deviation
corrects that belief using the already-measured historical anchoring pattern (the old
project's own finding, reusable here as a documented empirical constant, not re-derived):
real sellers' opening asks run approximately 50% above true reservation value; real
buyers' opening offers run approximately 25% below true valuation.

```
For a seller solving p* = argmax_{p≥V_A} (p−V_A)[1−F_B(p)]:
    F_B_corrected = F_B shifted so its implied median matches (observed or assumed
                    counterpart opening offer) / 1.25 instead of taken at face value
    p_dev = argmax_{p≥V_A} (p−V_A)[1−F_B_corrected(p)]

For a buyer facing a posted or robust price, apply the symmetric correction using
the 1.50 markup factor for a seller's opening ask.
```

This is deliberately a single, fixed, documented correction constant applied to the same
theoretical optimization — not a learned model — keeping it clearly distinct from
`π_EMPIRICAL` in §5, which is negotiation's fully learned deviation and is reserved for
the underdetermined cell only.

### 4.3 Persuasion

Four theoretical reference levels — confirmed against the primary source, which states
persuasion is fundamentally cheap-talk/no-commitment, not standard Bayesian persuasion:

- **P0 — Babbling equilibrium.** The actual no-commitment theoretical result (confirmed
  directly by the primary source: "it is well-known that the cheap-talk game only admits a
  babbling equilibrium"). Buyer ignores message entirely; buys iff `p ≥ 1/v`. **`π_theory(C)
  = P0` for every no-commitment persuasion cell — including repeated and multi-round
  cells, not only strict one-shot games.** The stage-game babbling result applies as the
  conservative per-round baseline throughout; repetition does not itself change the
  theoretical baseline. Repetition only opens the door to a *behavioral* deviation (P3,
  reputation) tested as a challenger — it never changes what `π_theory` is. Never treat P2
  as `π_theory` in any cell, repeated or not.
- **P1 — Full-disclosure benchmark.** Buyer buys iff quality is high. Reference value
  only, not an equilibrium (seller has incentive to misrepresent low quality) — never a
  deployable policy.
- **P2 — Bayesian-persuasion commitment benchmark** (Kamenica–Gentzkow). Upper bound
  under a commitment device GLEE's actual game does not have:
  `σ(buy|H)=1`, `σ(buy|L)=min{p(v−1)/(1−p), 1}`, value `= min(pv, 1)`. **Never treat this
  as the deployable baseline or as an achievable regret target** — it is a reference
  ceiling only.
- **P3 — Repeated-game reputation policy.** Not a theorem; a candidate behavioral
  deviation (`policies/persuasion/reputation.py`), tested via e-process against P0 as
  incumbent. **Available as a challenger in every repeated persuasion cell** — the earlier
  myopic-buyer restriction is removed, since (per §3.3's correction) the live competition
  does not expose a myopic buyer variant; every live buyer is history-aware, so there is
  no cell where P3 is structurally inapplicable. Concrete P3 formula, so this is fully
  implementable rather than only conceptual:
  ```
  history-based purchase rate so far this game: r_buy = (purchases) / (rounds so far)
  cap = 0.85     (v1 default — the highest fraction of high-quality-consistent messages
                  P3 will send even at its most exploitative; chosen default, not derived)
  early_rounds = first 30% of total_rounds (v1 default definition of "early")

  During early_rounds: always send the truthful recommendation (message reflects
  actual current_quality) — build reputation honestly.
  After early_rounds: recommend "buy" (or send a positive message) with probability
  min(cap, p + reputation_bonus), where reputation_bonus is a small positive
  constant (v1 default: 0.05) added only while the buyer's observed trust —
  approximated by their historical buy-rate on this seller's positive
  recommendations so far this game — exceeds the population average purchase
  rate on positive recommendations from the historical dataset for this cell.
  ```
  **Note on information use**: P3 is a *seller-side* policy — the seller always sees true
  quality and always observes the buyer's buy/no-buy decision each round (these are
  public outcomes, not private buyer information), so the "observed trust" proxy above
  uses only publicly observable buy/no-buy history, never the buyer's own private beliefs
  or anything the buyer's censored information (§3.3) would withhold. Persuasion's
  no-commitment theoretical baseline (P0) is a fixed threshold rule for the buyer with no
  adaptive component, so no buyer-side deviation is defined in v1; if one is added later,
  it must respect §3.3's quality-censoring — the buyer's own belief logic may condition
  only on rounds it actually purchased, never on unobserved quality.
  This is a simple, fully specified "honest-then-lean-on-earned-trust" rule — not a claim
  that it is optimal against a sophisticated backward-reasoning receiver (§4.3's own
  discussion already notes a fully rational receiver could unravel this); it is the
  concrete, testable hypothesis the e-process evaluates.

### Summary — locked deviation `B` for every cell, all three games

| Game | Cell(s) | Incumbent `A` | Deviation `B` | Defined in |
|---|---|---|---|---|
| Bargaining | All four rows in §4.1 | That row's `π_theory(C)` | Fairness concession (`δ_fair=0.10`) | `policies/bargaining/fairness.py` |
| Negotiation | Complete, `T=1` / finite-odd / finite-even | That row's `π_theory(C)` | Fixed surplus concession (`β=0.15`) | `policies/negotiation/fairness_margin.py` |
| Negotiation | Complete, unlimited/unknown | Midpoint convention (operational default) | Own-favorable anchor (`γ=0.65`) | `policies/negotiation/anchor_favorable.py` |
| Negotiation | Incomplete, `T=1` (trusted or ambiguous prior) | Bayes-optimal or robust price | Empirically-corrected price (fixed markup/shading constants) | `policies/negotiation/empirical_correction.py` |
| Negotiation | Incomplete, multi-round/unlimited | `π_BAYES` or `π_ROBUST` per §5.2 | Remaining §5 portfolio member(s) | §5 |
| Persuasion | Every no-commitment cell (repeated/multi-round) | P0 (babbling) | P3 (reputation, formula above) | `policies/persuasion/reputation.py` |

---

## 5. Deviation layer: BAYES / ROBUST / EMPIRICAL (negotiation's underdetermined cells)

For negotiation cells with no clean closed-form theory (incomplete-info multi-round,
incomplete-info unlimited horizon), lock exactly this three-policy portfolio.

### 5.1 Definitions

- **`π_BAYES`** (`policies/negotiation/bayes.py`) — Bayes-adaptive sequential pricing.
  Maintain a posterior `P_t(V_opponent)`, updated after every observed offer, rejection,
  acceptance, and message using a genuine response-likelihood model
  `P(reject | V_opponent, p, h)` — **not** naive threshold truncation (`reject ⟹
  V_opponent < p`), since a strategic opponent may reject a price they'd accept because
  they expect further concessions. If v1 ships a simpler threshold-response
  approximation, it must be explicitly labeled in code and docs as a
  **threshold-response approximation**, never presented as the exact Bayesian solution.
  Choose the action maximizing posterior expected payoff plus modeled continuation value.

  **Prior, locked**: `P_0(V_opponent)` follows a two-level rule, decided offline per
  `(cell, opponent-category)` alongside the eligibility check in §5.2:
  ```
  If historical data for this (cell, opponent-category) is adequate (reuse the same
  n≥200 threshold as §5.2's gate 1): P_0(V_opponent | C, τ) = the empirical
  historical distribution of that role's valuation for this (cell, τ).
  Otherwise: P_0(V_opponent | C) = discrete uniform over the verified legal
  valuation grid for that role in this cell.
  ```
  **`π_BAYES` is active and usable from the very first move of a game** — it does not
  wait for several in-game observations before acting; the prior alone is sufficient to
  produce a first action, and the posterior only sharpens from there via `Δ_instance`
  (§5.3).

- **`π_ROBUST`** (`policies/negotiation/robust.py`) — ambiguity-robust policy, **fully
  mechanical in v1, with no named behavioral archetypes and no learned component**. This
  is deliberate: `π_ROBUST` is the fallback incumbent whenever `π_BAYES` fails eligibility
  (§5.2) — i.e., precisely when a model-based or learned approach for that cell is not
  trusted — so `π_ROBUST` must not itself depend on any learned or empirical-population
  model. Construct the ambiguity set as a small, fixed, explicit grid of assumed opponent
  valuations spanning the cell's legal value range for the opponent's role (e.g. 5 evenly
  spaced points across the legal range, or quantiles of it — pick one fixed rule and apply
  it uniformly). Each grid point implies a simple, deterministic reservation-value
  acceptance rule: the hypothetical opponent accepts any offer at least as favorable to
  them as their assumed valuation. "Hardline" and "concessionary" are not separate models
  to build — they fall out automatically as the extreme ends of the same single grid.

  **Use minimax regret over the grid, not pure worst-case (maximin) payoff — this is a
  correction from an earlier version of this spec.** Pure maximin was checked directly
  during this spec's design and confirmed to degenerate: it always selects exactly the
  single lowest-valuation grid point, completely ignoring every other point in the grid,
  regardless of how the rest of the grid is composed (verified numerically — changing four
  of five grid points to wildly different values left the maximin-selected price
  unchanged). That makes "a small explicit grid of scenarios" pointless, since only one
  point of it ever matters. Minimax regret does not have this problem (verified
  numerically — it selects genuinely different prices depending on the grid's actual
  composition). Formally:
  ```
  𝒫_t = {g_1, ..., g_K}     — K fixed grid points over the opponent's legal valuation range
  For each g_k: opponent accepts price p iff p is at least as favorable to them
                as g_k would imply (concretely, for a seller choosing p: opponent
                (buyer) with assumed valuation g_k accepts iff p ≤ g_k)

  U_own(p, g_k)     — own payoff if the opponent's true valuation is g_k and we chose p
  best_possible(g_k) = max_p U_own(p, g_k)   — the payoff achievable if g_k were known
                        with certainty (i.e., pricing exactly at that scenario)
  regret(p, g_k)     = best_possible(g_k) − U_own(p, g_k)

  π_ROBUST = argmin_p  max_k  regret(p, g_k)
  ```
  subject to `p` ranging over the cell's legal price grid. No opponent-response model is
  learned or estimated from data anywhere in `π_ROBUST` — every input is derived directly
  from the configuration's legal value range. Document this exact formulation, including
  the degeneracy finding and why regret was chosen over pure maximin, in
  `docs/theory_baselines.md` under a labeled "ROBUST v1 fallback policy" section — this is
  a deliberately conservative fallback decision rule, not a claimed equilibrium solution.

  **`π_ROBUST`'s ambiguity set is static for the duration of a game**: `𝒫_t = 𝒫_0`
  throughout — it does not shrink, reweight, or Bayes-update the grid based on observed
  history. It may choose a different action round to round only because the current legal
  action set, round/horizon position, or current proposal on the table differs — never
  because it revised its belief about the opponent. This is a deliberate consequence of
  `π_ROBUST`'s purpose as the model-light fallback: if it started belief-updating, it
  would no longer be the "no learned/adaptive component" option BAYES's eligibility
  failure calls for.

- **`π_EMPIRICAL`** (`policies/negotiation/empirical.py`) — theory-anchored empirical best
  response. Train `P̂(a_opponent | C, h_t, a_t, τ)` from the historical dataset; choose the
  action maximizing predicted payoff, **subject to a support/out-of-distribution penalty**
  (`Q_EMP(p) = Ê[U|p,h] − λ_OOD · OOD(p,h)`) so it never confidently extrapolates into
  actions scarcely represented historically. **Within a game, `π_EMPIRICAL`'s trained
  model parameters never change — only its input `h_t` grows as the game proceeds.**
  Feeding a longer, fresher history into an otherwise-frozen model is history
  conditioning, not retraining; do not conflate the two (see the freeze rule below for
  the across-game distinction, which is the one that actually matters for statistical
  validity).

**Model training and artifacts** (`π_BAYES`'s likelihood model, `π_EMPIRICAL`'s response
model): both are genuine fitted statistical models and need a real training workflow, not
an implicit one:

```
research/
├── training/
│   └── negotiation/
│       ├── train_bayes_response.py       # fits P(reject | V, p, h) per (cell, τ)
│       └── train_empirical_response.py   # fits P̂(a_opponent | C, h_t, a_t, τ)
```

```
data/
└── processed/
    └── models/
        └── negotiation/
            └── <cell>/<opponent_category>/<version>/
```

Each trained artifact must record, at minimum: training-data snapshot/hash, cell,
opponent category, prior (for BAYES), the fitted likelihood/response model, the
calibration transform (BAYES only, per §5.2), measured BSS, a model version identifier,
and the code commit that produced it. The exact model family for each (linear, tree-based,
etc.) is ordinary implementation discretion, not something this spec locks — what must
not be ambiguous is that model weights are frozen before any e-process test begins, which
the rule below makes explicit.

**No model parameter changes during an active testing round — this is a hard rule, not a
preference.** Before an e-process (§6) begins accumulating evidence in a given cell,
freeze: the BAYES prior and likelihood parameters, the calibration mapping, the EMPIRICAL
model's parameters, its OOD threshold, and any feature preprocessing. New live games may
be logged into a future training dataset, but they must never silently modify the
candidate currently under test. **If a model is retrained, that is a new policy, not an
update to the old one**: `B^(v1) → B^(v2)` requires a new experiment ID and a fresh
`E_0 = 1` — never continue accumulating evidence for a retrained model under an existing
experiment's running `E_t`. Record the model version in the experiment registry (§7.3)
alongside the usual fields, so which exact frozen artifact a given experiment's evidence
refers to is always traceable.

### 5.2 BAYES eligibility (offline, per cell, one-time)

`π_BAYES` is the default incumbent for an underdetermined cell **only if both quantitative
eligibility gates hold, and the specified calibration procedure has been completed
without failure**, on held-out historical data for that cell:

```
n_historical_games_in_cell ≥ 200                                          [gate 1]
BSS ≥ 0.10   (Brier Skill Score of the response-likelihood model vs. the cell's
              unconditional population rejection rate as naive baseline)   [gate 2]

required procedure (not a third numeric gate): fit the response model on
training data, calibrate probabilities on a validation split via Platt or
isotonic calibration, then assess BSS (gate 2 above) on an untouched held-out
test set. Calibration is part of the model-fitting pipeline, not an
independent pass/fail threshold — do not add an ECE or other calibration
cutoff unless a specific value is separately justified; "BSS alone is not a
calibration criterion" (per the Brier-score decomposition into reliability
minus resolution plus uncertainty) is why the calibration *step* is required
in the pipeline, not evidence that a third gate is needed.
```

If either gate 1 or gate 2 fails, `π_ROBUST` is the incumbent for that cell instead.

**A `π_BAYES` that fails this eligibility check is excluded from live testing in that
cell entirely — not merely disqualified from being incumbent.** Do not test a
failed-eligibility BAYES as challenger `B` against `π_ROBUST` either: the same defect
that disqualified it from being incumbent (insufficient historical support, or poor
calibration) means there is no more reason to trust it as a live challenger than as a
default. In that case the only live comparison for the cell is `π_ROBUST` (incumbent)
vs. `π_EMPIRICAL` (challenger, `M=1`).

This eligibility check is computed once, offline, per cell — never re-evaluated live or
based on in-game observation count.

### 5.3 `Δ_instance` — what it actually is, and the layering resolution

To keep instance-level adaptation from regressing into the removed heuristic
mode-switching system (no `SAFE`/`EXPLORE`/`EXPLOIT`/`COMMIT` states, no hand-tuned
multipliers, no within-opponent e-processes — none of these are being built):

1. `Δ_instance` performs only genuine Bayesian updating: a stated prior, a stated
   likelihood, Bayes' rule. No hand-tuned adjustment constants without a stated
   derivation.
2. Its output is always a **number** plugged back into the active policy's formula
   (e.g., a re-estimated valuation) — never a code-path or mode switch.
3. Only the population-level e-process (§6–§8), using evidence accumulated across many
   games, may change which named policy is active for a cell. `Δ_instance` never uses
   evidence from only the current, in-progress game to switch policies.

**Resolving the layering ambiguity, explicitly.** The master formula in §1 —
`π_t = π_theory(C) + Δ_population(C,τ) + Δ_instance(h_t) + Δ_communication(...)` —
describes a **conceptual decomposition of where each kind of adaptation lives**, not a
literal sequence of arithmetic operations applied one after another to every policy.
Concretely, per policy:

- **`Δ_population` determines *which named policy* is active** for the cell (theory
  itself, or a promoted deviation like BAYES/ROBUST/EMPIRICAL/fairness/reputation/etc.).
  This is the only layer that can *switch* policies, and only via the e-process (§6–§8).
- **`Δ_instance` is that active policy's own legitimate within-game conditioning
  mechanism** — it is not a universal second optimizer bolted on afterward. Concretely:
  - When `π_BAYES` is active, its own posterior update *is* `Δ_instance` for that game.
    **Do not apply any separate, generic `Δ_instance` mechanism on top of BAYES's own
    posterior update — that would double-update the same belief and is explicitly
    disallowed.**
  - When `π_EMPIRICAL` is active, feeding the frozen model a growing `h_t` each round *is*
    `Δ_instance` for that game — again, nothing further is bolted on top.
  - When `π_ROBUST` is active, there is **no `Δ_instance` content in v1** — per §5.1,
    `π_ROBUST`'s ambiguity set is static for the game, so this policy has nothing for
    `Δ_instance` to update.
  - When a purely-theoretical policy is active (e.g. exact backward induction, babbling),
    `Δ_instance` likewise has no content unless that specific cell's incumbent is one of
    the belief-updating policies above — theory itself doesn't have beliefs to update.

So: `Δ_instance` is never a separate module invoked identically regardless of which
policy is active. It is a *label* for whatever within-game conditioning the active
policy already does, natively, as part of its own definition — and for `π_ROBUST` and
pure-theory incumbents, that label currently has nothing under it.

---

## 6. E-process construction (the anytime-valid statistical test)

`eprocess/betting.py` — pure math, knows nothing about GLEE, games, policies, or
configurations.

**Purpose, precisely**: given one configuration cell and two named policies (incumbent A,
candidate B), accumulate anytime-valid evidence on whether B has higher expected
normalized payoff than A. It does not choose which theoretical baseline applies (§4
already fixed that from configuration alone) and it does not perform within-game opponent
classification.

### 6.1 Setup

- Requires **randomized 50/50 assignment** between A and B for comparable games in the
  cell. **Do not** feed this construction observational outcomes from an adaptive
  selector that preferentially plays B in favorable states — if unequal assignment is
  ever needed, that requires an explicitly propensity-corrected construction, not this
  one.
- **One e-process instance = one fixed `(cell, opponent-category, incumbent, candidate)`
  tuple.** Do not pool `human`/`agent`/`hidden` observations into a single running
  process for the same cell — each opponent-category stratum gets its own independent
  e-process instance, its own `E_t`/`E_t'`, and its own persisted log (§6.5). This is the
  concrete, enforced version of the stratification rule below; it is not optional.
- Stratify/randomize within the relevant (configuration, opponent-category) stratum —
  never let treatment assignment become confounded with configuration. `hidden` is its
  own observed stratum, on equal footing with `human` and `agent` — do not attempt to
  infer a latent true category for a `hidden` opponent and fold it into the `human`/`agent`
  strata for randomization purposes; the API's disclosure mechanism is itself random, so
  treating `hidden` as a distinct, real stratum is the correct and simpler choice.
- Convert each realized game's own payoff to `Y_t ∈ [0,1]` using the mechanism-derived
  normalization from §9. The normalization rule is fixed from configuration and role —
  never from observed outcomes, never dependent on which policy was used.
- Use a dedicated, explicitly seeded RNG instance per experiment for A/B assignment —
  never draw from unseeded global random state. Log every assignment (experiment id,
  cell, timestamp, arm assigned) to persistent storage (§6.5) *before* the game's outcome
  is observed, so assignment history is fully reconstructible and auditable independent
  of outcomes. Store the experiment's seed alongside its other configuration.
- **Log concurrency alongside every experiment.** The matchmaker's opponent mix may not
  be entirely independent of concurrency settings (queueing/dispatch behavior can differ
  when multiple games run in parallel versus one at a time) — this is a plausible
  confound worth guarding against even where the exact mechanism isn't fully pinned down.
  Log the concurrency level, game-family queue selection, timestamp, and disclosed
  opponent category (or `hidden`) for every game in an active experiment, and **keep
  concurrency fixed for the duration of a single testing round** where practical — do not
  change concurrency mid-experiment and treat the resulting games as drawn from the same
  distribution without checking.

### 6.2 Update rule

```
Z_t = +1 if candidate B was assigned this game, −1 if incumbent A was assigned
X_t = Z_t · Y_t                                  (∈ [−1, 1])

H0: E[Y(B) − Y(A) | F_{t−1}] ≤ 0

For λ ∈ Λ = {0.1, 0.25, 0.5, 0.75}:
  E_0^(λ) = 1
  E_t^(λ) = E_{t−1}^(λ) · (1 + λ·X_t)     [updated after every completed game]

E_t = (1/4) · Σ_λ E_t^(λ)
```

This is a nonnegative test supermartingale under `H0` for each λ (bounded-mean betting
construction, Waudby-Smith–Ramdas family); a convex mixture of valid e-processes remains
valid. Do not implement adaptive betting-fraction tuning — the fixed four-point mixture is
the deliberate v1 choice. Do not substitute a differently-scaled or inverse-propensity
variant of this formula — under 50/50 assignment, `X_t = Z_t·Y_t` is already the correct
Horvitz-Thompson-style contrast; any equal-propensity rescaling of it (e.g. multiplying by
2) is the same estimator, not a distinct or more correct one.

**Why this is valid — state this explicitly in code documentation, not just here.**
Writing `Y_t(A)`, `Y_t(B)` for the (only one of which is ever observed) potential
normalized payoffs under each policy for game `t`:

```
E[X_t | F_{t−1}] = E[Z_t · Y_t | F_{t−1}]
                 = ½·E[Y_t(B) | F_{t−1}] − ½·E[Y_t(A) | F_{t−1}]
                 = ½·(E[Y_t(B) | F_{t−1}] − E[Y_t(A) | F_{t−1}])
                 ≤ 0   under H0
```

This equality requires exactly two conditions — both already required elsewhere in this
spec, restated here as the precise reason they matter:

1. **`Z_t` is generated by an independent, pre-committed randomization** (a fresh 50/50
   draw, decided before the game is played, not depending on `F_{t−1}` or on either
   potential outcome). This is why §6.1 requires a dedicated seeded RNG and logging the
   assignment before the outcome is observed — it is not a procedural nicety, it is the
   condition that makes the derivation above hold.
2. **Only the realized arm's outcome is used** — `Y_t` is `Y_t(B)` when B was assigned,
   `Y_t(A)` when A was assigned, never both, never an imputed or model-based value.

**If assignment is ever adaptive or confounded with outcomes, this construction is
invalid**, not merely suboptimal — an adaptive selector that preferentially assigns B in
favorable states breaks the derivation above and can produce a badly miscalibrated
process (in a direct simulation check during this spec's design, deliberately confounded
assignment inflated `E[E_T]` under an exactly-true null from the expected ~1 to ~13 — a
genuine validity failure, not a small effect). This is exactly why §6.1 already prohibits
feeding this construction observational outcomes from an adaptive selector; that
prohibition is load-bearing, not precautionary.

**Required test, before this module is used for any promotion decision**: a synthetic-null
simulation — many independent replications of a sequence of games with `Y_t(A)` and
`Y_t(B)` drawn from distributions with an *exactly equal* mean, honest 50/50 pre-committed
assignment — confirming empirically that (a) the average final `E_T` across replications
stays near 1, and (b) the empirical rate of `E_T` crossing `1/α_test` stays at or below
`α_test`. This is a required part of `tests/eprocess/`, not optional.

**Formal checklist — every item explicitly stated, for `docs/eprocess_math.md`.** This is
a restatement/index of what's already derived above, not new content, collected here as
an explicit checklist so nothing is left implicit:

```
Filtration F_{t-1}:            all information available immediately before game t's
                                assignment is drawn (prior games' assignments and
                                outcomes in this experiment).
Assignment timing:             Z_t is drawn fresh, independently, before game t is
                                played — never after or influenced by Y_t.
Assignment probability:        P(Z_t=+1) = P(Z_t=-1) = 1/2, independent of F_{t-1}.
Potential outcomes:            Y_t(A), Y_t(B) — the normalized payoff that would result
                                under each policy for game t; only one is ever realized.
Observed outcome:               Y_t = Y_t(B) if Z_t=+1, Y_t(A) if Z_t=-1.
Null hypothesis:                H0: E[Y_t(B) - Y_t(A) | F_{t-1}] ≤ 0.
Betting variable:               X_t = Z_t · Y_t.
Conditional expectation:        E[X_t | F_{t-1}] = ½(E[Y_t(B)|F_{t-1}] - E[Y_t(A)|F_{t-1}])
                                 ≤ 0 under H0 — derived above.
Bounded support:                X_t ∈ [-1, 1], since Y_t ∈ [0,1] and Z_t ∈ {-1,+1}.
Allowable betting fractions:    for every λ, need 1+λX_t ≥ 0 for all X_t in [-1,1]; the
                                 binding case is X_t=-1, giving 1-λ≥0, i.e. λ<1 required.
                                 All four fixed values in Λ={0.1,0.25,0.5,0.75} satisfy
                                 this with room to spare (worst case at λ=0.75:
                                 1+0.75·(-1)=0.25≥0) — confirmed by direct computation
                                 during this spec's design, not merely asserted.
```

This construction (`X_t = Z_t·Y_t`) was checked against this exact checklist during this
spec's own design process, including numerical simulation under an exactly-true null
(confirmed `E[E_T]≈0.98`, near the theoretical 1) and under deliberately confounded/
adaptive assignment (confirmed `E[E_T]` inflates to ~13, correctly demonstrating the
construction's validity depends on honest randomization, exactly as required by
condition 1 above). **It is not an open or unverified question — do not re-derive from
scratch or substitute a different contrast** (e.g., an inverse-propensity-rescaled
version) on the assumption that this hasn't been checked; it has, both analytically and
numerically, and a rescaled version of the same estimator would not change the
conclusion. `docs/eprocess_math.md` must reproduce this checklist and both derivations
(the validity derivation and the confounding counter-example) verbatim as the permanent
record — do not treat producing that file as license to reopen the math.

### 6.3 Promotion criterion — two requirements, both must hold

```
E_t ≥ 1/α_test                    (statistical evidence — see §7 for α_test)
Δ̂U = Ê[Y_B − Y_A] > Δ_min          (practical effect size)
```

`Δ_min = 0.01` on the normalized `[0,1]` payoff scale is the locked v1 default — chosen
for the same reason as `n≥200`, `BSS≥0.10`, and `α_family=0.05`: a deliberately chosen,
simple starting value, not a derived or provably optimal number. Expose it as a named
config constant (`eprocess/experiment.py` or a shared config module), not a hardcoded
literal, so it can be revisited later without a code change.

### 6.4 Three legitimate outcomes — formalized, all mechanically deterministic

The §6.2 construction as given is one-sided (evidence that B beats A). To make `RETAIN`
mathematically defined rather than a prose judgment call, run its exact mirror alongside
it, reusing the identical machinery with the sign flipped:

```
Main process   (evidence B beats A):   X_t   = Z_t · Y_t     → E_t
Mirror process (evidence A beats B):   X_t' = −Z_t · Y_t    → E_t'
```

`E_t'` is computed with the same update rule, same `Λ` mixture, same `α_test`, as an
entirely separate running e-process over the same stream of assignments/outcomes. Then:

```
PROMOTE       — E_t ≥ 1/α_test  AND  Δ̂U > Δ_min   (§6.3, evidence favors B, with
                practical significance)
RETAIN        — E_t' ≥ 1/α_test                    (evidence favors A — the
                incumbent — crosses its own threshold on the mirror process)
INCONCLUSIVE  — the experiment window closes (no more live games available for
                that cell in the remaining competition period) with neither E_t
                nor E_t' having crossed 1/α_test
```

**RETAIN deliberately does not require a `Δ_min` margin in v1.** This asymmetry is
intentional, not an oversight: the burden of proof belongs on the side proposing a
change (`PROMOTE`, which requires both statistical *and* practical significance), not on
the side of keeping the status quo. Any evidence that the incumbent is at least as good
is sufficient to retain it, since deploying a change carries engineering and strategic
risk that the current architecture is otherwise careful to require strong justification
for (see the "adapt slowly in policy" principle governing `Δ_instance` in §5.3). Do not
"symmetrize" this by adding a `Δ_min` requirement to `RETAIN` — that would understate how
much evidence favors keeping a working incumbent.

All three outcomes are now fully determined by the same two numbers (`E_t`, `E_t'`)
against the same threshold — no separate "clearly favors" judgment is required anywhere.

**INCONCLUSIVE is not FAILED. The incumbent remains deployed for that cell.** Do not
lower e-value thresholds, multiplicity corrections, `Δ_min`, or any other promotion
criterion retroactively to force a PROMOTE or RETAIN outcome. State plainly in
`docs/experiment_registry.md` if this occurs for a given cell — it is a legitimate,
reportable finding about evidentiary discipline under a time constraint, not a defect.

### 6.5 Persistence

Persist e-process state as **append-only JSONL**, one file per experiment
(`experiment_id`), one line per completed game, with every field needed to reproduce that
single line's contribution without cross-referencing other files: `{experiment_id, cell,
opponent_category, incumbent, candidate, experiment_seed, timestamp, assigned_arm,
assignment_probability, raw_payoff, Y_t (normalized), X_t, X_t', E_t^(λ) for each λ,
E_t'^(λ) for each λ, running E_t, running E_t'}`. On process restart, reload state by
replaying the log deterministically from the start (do not persist only the final running
totals — the full per-observation log is the source of truth, enabling both crash
recovery and independent audit/replay of the exact sequence of evidence). This is a
deliberately simple choice over a database, consistent with this spec's general
preference for the simplest auditable mechanism.

---

## 7. Multiplicity control

### 7.1 Within-cell promotion (Bonferroni)

`M` = the number of simultaneous candidate-vs-incumbent promotion hypotheses tested
**within one cell against its current incumbent, in one testing round**. `M` equals the
exact count of challengers being simultaneously tested against that cell's current
incumbent — not the total size of the named policy portfolio. `M` is a fixed
configuration constant, set once per cell per testing round, not recomputed
opportunistically based on which tests happen to have live data today.

```
α_family = 0.05   (fixed default)
α_test = α_family / M
```

Worked examples, arithmetic checked:
- One challenger against the incumbent (`M=1`): `α_test = 0.05 → E_t ≥ 20`.
- Two challengers against the incumbent (`M=2`) — e.g. `π_BAYES` is the eligible
  incumbent for a cell (§5.2) and both `π_ROBUST` and `π_EMPIRICAL` are simultaneously
  tested as challengers against it: `α_test = 0.025 → E_t ≥ 40`.
- Three challengers against the incumbent (`M=3`) — e.g. `π_THEORY` is incumbent and
  `π_BAYES`, `π_ROBUST`, `π_EMPIRICAL` are all simultaneously tested against it:
  `α_test = 0.01667 → E_t ≥ 60`.

Do not apply Bonferroni across every cell in the system simultaneously — that conflates
exploration with confirmation and is unnecessarily conservative. See §7.2.

### 7.2 Exploration vs. within-cell confirmation — and why there is no "final cell"

```
Explore many cells → promote/reject/inconclude within-cell (§7.1) → confirm the
winning policy per cell on fresh data → deploy via the policy map (below)
```

**Correction to an earlier version of this spec: there is no "select the final cell to
deploy into" step, and no cross-cell selection procedure.** Matchmaking assigns a
configuration cell to each arriving game — you queue for a *family*
(`bargaining`/`negotiation`/`persuasion`), never for a specific cell (§3.4). Deploying
"into" one chosen cell was never an available action, so a procedure for choosing among
cells to deploy into was solving a decision this system doesn't actually control. This
spec's earlier "cross-cell confirmation via simultaneous Bonferroni LCBs, selecting
`C* = argmax_C LCB_C`" is removed for that reason, not because the statistics were wrong
— the statistics were fine, they were just answering a question with no corresponding
deployment action.

What replaces it:

- **Exploration**: any number of cells may be continuously monitored via their own
  e-process. Each individually pre-specified e-process is anytime-valid under optional
  stopping — watching it accumulate costs nothing statistically.
- **Same-cell confirmation** (choosing between finalist *policies* within one specific
  cell — this part is unaffected, since which policy is active for a given cell **is**
  something we control): reuse the identical §6 betting e-process one more time, on
  strictly fresh post-freeze data, `M=1` (threshold `E_t ≥ 20` at `α=0.05`).
- **The policy map**: every cell independently arrives at its own current best-supported
  policy through the within-cell promotion process (§7.1) plus same-cell confirmation
  above. There is no comparison *across* cells and no "winner" among them. Deployment is
  simply: `(C, τ) ↦ π*_{C,τ}` — for whatever cell and opponent-category an arriving live
  game presents, route to that cell's currently-promoted (or default) incumbent. This is
  `leaderboard/policy_router.py`'s actual job (§1, §2): look up the arrived game's
  `(cell, opponent-category)`, dispatch to its current policy, adapt within-game per
  `Δ_instance` (§5.3), communicate if applicable (leaderboard agent only).
- **Cell prioritization (§8) still matters** — live games are scarce, and not every
  arriving game needs to be randomized into an active experiment — but its purpose is
  "which arriving cells are worth spending scarce randomized live games on," not "which
  cell should eventually win." See §8's restated framing.

### 7.3 Experiment registry schema

`docs/experiment_registry.md` (and/or a machine-readable counterpart such as
`docs/experiment_registry.jsonl`, one row per experiment) must record at minimum, for
every experiment run:

```
experiment_id        — unique identifier
cell                  — the (game, configuration) this experiment tests
opponent_category     — human | agent | hidden (the fixed stratum this experiment
                        instance covers, per §6.1's one-instance-per-stratum rule)
incumbent             — named policy (e.g. π_BAYES)
candidate             — named policy being tested against the incumbent
model_version         — frozen model artifact version(s) under test, for any
                        candidate/incumbent involving a trained model (§5.1) —
                        required whenever BAYES or EMPIRICAL is involved
alpha_family          — 0.05 unless explicitly overridden
M                     — challenger count for this testing round, per §7.1
alpha_test            — alpha_family / M
delta_min             — 0.01 unless explicitly overridden
data_window           — start/end timestamps of games included
n_games               — number of completed randomized games in this experiment
E_t_final             — final main-process e-value
E_t_prime_final       — final mirror-process e-value
effect_estimate       — Ê[Y_B − Y_A]
outcome               — PROMOTE | RETAIN | INCONCLUSIVE
active_policy         — whichever policy is active for this (cell, opponent_category)
                        as of this experiment's resolution — this is what the policy
                        map (§7.2) actually reads
code_commit           — commit hash of the code state this experiment ran under
```

The registry's role, precisely: it records **which policy currently has evidentiary
status for each `(cell, opponent_category)`**, backing the policy map. It never records
"which cell won," because no cell ever competes against another cell.

A policy is not leaderboard-eligible until its promotion is recorded here per §2's
promotion rule.

---

## 8. Cell prioritization (live-experiment allocation)

**Reframed purpose, consistent with §7.2's correction**: the question this section
answers is *"which arriving cells should be randomized into an active live experiment
versus simply served by their current default/incumbent policy"* — not "which cell should
eventually win" (there is no cross-cell winner; see §7.2). Matchmaking gives you a game
family, not a specific configuration cell, and live randomized games are the scarce
resource (offline historical data can be used to analyze *every* cell; live
experimentation cannot cover all of them in the time available). Use this to decide which
cells receive live experimental games first.

```
Δ̂_C  = offline-estimated payoff gap, best challenger minus current incumbent, for cell C
SE_C  = standard error of Δ̂_C

p_C = Φ(Δ̂_C / SE_C)              (approx. probability the challenger truly beats incumbent)
D_C = p_C · (1 − p_C)             (decision uncertainty — peaks at p_C=0.5, → 0 as the
                                    decision becomes obvious in either direction)

Priority(C) = occurrence(C) × |Δ̂_C| × D_C
```

Where `occurrence(C)` = historical frequency of cell `C` in the ingested dataset, used as
an initial proxy for expected live-matchmaking frequency. Document this explicitly as an
assumption, not a proven fact:
`occurrence_hat(C) = historical_frequency` initially; update from observed live
matchmaking frequencies as competition data accrues.

**Do not** use `Δ̂_C / SE_C` (a t-statistic) alone or `Δ̂_C / SE_C × occurrence(C)` as the
priority score — this rewards cells that are already confidently resolved (where
additional live games have low information value) over cells where genuine
decision-relevant uncertainty remains. The `D_C = p_C(1−p_C)` term is what correctly
captures "would another observation plausibly change the decision," which is the actual
quantity of interest for allocating scarce experiments.

`SE_C` computation: **nonparametric bootstrap over complete historical games in cell C**
(resample whole game trajectories, never individual turns — turns within one game are
sequentially dependent, so turn-level resampling understates true variance). If stable
opponent identities exist and repeated games from the same opponent are present in the
data, cluster the bootstrap by opponent identity. Use model-based prediction variance only
as a fallback when bootstrap estimation is infeasible.

When computing `Φ(z)` for large `|z|` (e.g. `z ≥ 8` or so), treat the result as
numerically saturating at 0 or 1 for ranking purposes — do not present it as exactly 0 or
1 in any documentation or log output; state it as "effectively certain," not "certain."

---

## 9. Payoff normalization (`glee/normalization.py`)

Implement **one generic normalization function** based on configuration-derived payoff
bounds, not three separately hardcoded per-game conventions:

```
Y = (U − U_min(C, r)) / (U_max(C, r) − U_min(C, r))     ,  Y ∈ [0, 1]
```

Bounds must be derived from the **configuration and role**, never from realized outcomes
or historical maxima.

- **Bargaining**: `U_min = 0`, `U_max = M` (own payoff ranges from 0 to the full pot).
- **Negotiation**: given the legal price range `[p_min, p_max]` for the cell:
  - Seller: `U_min,S = min(0, p_min − V_S)`, `U_max,S = max(0, p_max − V_S)`.
  - Buyer: `U_min,B = min(0, V_B − p_max)`, `U_max,B = max(0, V_B − p_min)`.
  - These are the general, mechanism-safe bounds — they allow for negative realized
    utility, since nothing in the mechanism guarantees a legal offered/accepted price
    respects either party's reservation value. They correctly reduce to the simpler
    `[0, p_max − V_S]`-style bounds only in the special case where `p_min ≥ V_S` (or
    symmetrically for the buyer) actually holds.
  - **VERIFY-FIRST**: determine the exact legal negotiation price action space from the
    GLEE mechanism/SDK. Confirm whether `(p_min, p_max)` is finite, whether `M` defines
    those bounds directly, and whether accepted trades can in fact yield negative
    utility under the real mechanism. Instantiate the formula above from whatever is
    verified. If no finite legal bound is exposed at all, do not fabricate one (e.g. do
    not silently substitute a historical observed maximum) — stop and report per the
    top-level VERIFY-FIRST protocol.
- **Persuasion**: derive minimum/maximum attainable cumulative payoff directly from the
  configuration's stage-payoff table (`p`, `v`, price, `M`) and horizon `T`, then apply
  the same generic transformation.

---

## 10. Verification tasks (VERIFY-FIRST — resolve before dependent code is written)

The items below require inspecting the actual GLEE SDK/API, not just the paper — see
"Repository and execution context" at the top of this document. If the exact SDK source
is not yet supplied when this work is reached, mark the relevant item BLOCKED in
`docs/verification_log.md` rather than verifying against the paper alone or guessing.
Each item is also flagged inline at its point of use above.

**One item resolved since the previous version of this spec, no longer VERIFY-FIRST**:
the persuasion myopic/long-living axis (confirmed absent from the live competition, per
§3.3's correction) — independently confirmed against documentation already reproduced in
this spec, not merely relayed secondhand. **The e-process construction (§6.2) is likewise
not a VERIFY-FIRST item** — it was mathematically derived and numerically verified during
this spec's own design process (see §6.2's checklist and `docs/eprocess_math.md`
requirement); do not reopen it as unverified.

**One item partially walked back**: opponent-type enum. `"agent"` and `"hidden"` are
confirmed via literal JSON examples; the literal string for the disclosed-human case is
inferred from prose only (§3.4) — see item 4 below.

**Unresolved conflict, flagged rather than silently resolved**: two different sources in
this spec's own design history disagree on the GLEE API credential's environment variable
name — one says `GLEE_API_KEY` (attributed to the SDK README), another says
`GLEE_API_TOKEN`. The current "Repository and execution context" section uses
`GLEE_API_KEY`. **Confirm the actual variable name against the real SDK/docs before
relying on either — this needs a human decision or direct source check, not a guess.**

1. **Negotiation finite-horizon parity mechanics.** Downgraded from a large live-data
   spot-check to a lighter implementation/source verification: confirm from direct SDK or
   validator source inspection (not necessarily 20-30 live games, if source inspection is
   unambiguous — fall back to the live-game spot-check only if source inspection doesn't
   settle it) that Alice proposes odd stages / Bob proposes even stages as documented,
   that round numbering starts at 1, and specifically that at `max_rounds=10` Bob is the
   terminal proposer. If this contradicts the assumed parity, stop the dependent theory
   branch (§4.2, complete-info finite-even-T row) and report the discrepancy — do not
   silently adjust the formula.

2. **Negotiation legal price bounds.** As detailed in §9 above — still the most important
   remaining mechanism-level item. Inspect `valid_actions["fields"]` at runtime and/or
   validator/game-config source directly; do not substitute a historical observed maximum.

3. **SDK transport interface** (`glee_sdk.GleeClient`, per "Repository and execution
   context"). Confirm the exact package/class/method surface before building
   `glee/client.py` around it; fall back to the originally specified custom
   client/retry implementation if it doesn't match. **Also confirm the exact API-key
   environment variable name while resolving this item** (see the conflict flagged
   above) — do not proceed with either candidate name unconfirmed.

4. **Opponent-type enum, human case.** Confirm the literal JSON value returned for a
   disclosed-human opponent (assumed `"human"`, per prose description only) against one
   real disclosed-human game payload. Cheap, light-weight — not the larger unknown this
   item originally was before `"agent"`/`"hidden"` were confirmed via direct examples.

**`docs/verification_log.md` entry format**, for every item above: record `item`, `source
inspected`, `result` (one of `CONFIRMED` / `CONTRADICTED` / `BLOCKED`), `evidence`,
`dependent components` (what in this spec relies on this fact), and `action taken`.

---

## 11. What is explicitly out of scope — do not build

- No heuristic mode-switching state machine (no `SAFE`/`EXPLORE`/`EXPLOIT`/`COMMIT`
  states, no hand-tuned `E_fairness`/`E_concessionary`-style multipliers).
- No within-opponent-instance e-process (no attempt to accumulate anytime-valid evidence
  about one specific opponent within or across their individual games — persistent
  opponent identity for this purpose is not reliably available). The e-process operates
  at the population level only, per §6–§8.
- No `Δ_communication` in the research agent, under any framing.
- No risk-scaled or variable promotion threshold (considered and explicitly rejected in
  favor of the simpler uniform `α_test` per §7.1 — this is a deliberate simplicity
  decision, not an oversight).
- No treating Bayesian persuasion (P2) as the deployable persuasion baseline — P0
  (babbling) is `π_theory` for persuasion; P2 is a reference ceiling only.
- No treating any negotiation/bargaining incomplete-information "solution" as an exact
  equilibrium where this document labels it an approximation (certainty-equivalent,
  Bayes-adaptive, threshold-response, etc.) — carry the approximation label into code
  comments and docs, not just this spec.
- No per-opponent-name conditioning for `Δ_population` in v1 — category-level only
  (`human`/`agent`/`hidden`). Per-name conditioning would multiply cell count and evidence
  requirements beyond what the timeline supports.
- No historical-outcome-based normalization bounds (e.g., using an observed historical
  maximum price as a stand-in for a mechanism bound) — normalization must be
  mechanism-derived only, per §9.

### What is ordinary implementation discretion (not something to ask about)

This spec freezes strategic and statistical semantics; it does not freeze ordinary
software-engineering choices. Codex has full discretion over: exact class names,
dataclass vs. plain class, internal helper function structure, logging library, HTTP
client library (unless §10 item 3 resolves this), CLI argument parser, serialization
helper implementation, test fixture organization, and type-hint style. Do not pause for
review merely because one of these is unspecified — pick something reasonable and move
on. **What is not discretionary**: game theory and theoretical baselines (§4), policy
definitions (§4's locked deviations, §5), experimental treatment assignment and
statistical nulls (§6), promotion criteria and multiplicity treatment (§6–§7),
normalization (§9), dataset source (§"Repository and execution context"), the
research/leaderboard separation (§2), and VERIFY-FIRST handling (§10). If uncertain
whether something falls on the discretionary or frozen side, treat it as frozen and
follow the spec as written rather than guessing.

---

## 12. Build order

1. Inspect the target repository (`SaharArora/Workings`) — confirm it is actually empty
   before assuming so; report anything unexpected found rather than overwriting silently.
2. Create/confirm the project skeleton (§2) and Python environment (§"Repository and
   execution context").
3. `glee/` — API client, schemas, retry/backoff. Get this working and tested against the
   real API first (queue, poll, submit, stats) since everything else depends on it.
4. Resolve VERIFY-FIRST items #1–#3 (§10, mechanism items) before writing theory/
   normalization code that depends on their outcomes.
5. Inspect the actual `Data/` structure in `eilamshapira/GLEE`.
6. **Targeted negotiation-cell ingestion and profiling** (per the targeted-first strategy
   in "Repository and execution context"): ingest negotiation cells first, count games per
   cell, check `n≥200` eligibility (§5.2), profile file count/bytes/parse time before
   deciding whether to expand further. Do this now, ahead of policy implementation, so
   `π_BAYES`/`π_EMPIRICAL` (step 11 below) can be designed and tested against real records
   where available, not synthetic fixtures alone.
7. `theory/` per §4, with unit tests against hand-computed cases for every cell —
   including the bargaining finite-horizon recursion in §4.1, tested against small `T`
   (e.g. `T=1,2,3`) by hand computation, and checked that it converges toward the
   infinite-horizon Rubinstein formula as `T` grows.
8. `glee/normalization.py` per §9.
9. `eprocess/betting.py` (pure math; test against the worked numerical examples and the
   formal checklist in §6.2 — do not re-derive or substitute a different construction) and
   `eprocess/experiment.py`. Produce `docs/eprocess_math.md` per §6.2's requirement.
10. `policies/negotiation/robust.py` using the minimax-regret formulation (§5.1, not pure
    maximin — document the degeneracy finding in `docs/theory_baselines.md`).
11. `policies/negotiation/bayes.py` and its offline eligibility pipeline (§5.2), using
    whatever targeted data step 6 produced.
12. `policies/negotiation/empirical.py`, **only for cells with sufficient historical
    support**; mark cells without it explicitly `BLOCKED` rather than training against
    fabricated or synthetic historical data to make the component appear complete.
    **A per-cell `BLOCKED` status is an acceptable and preferable outcome to fake
    completeness — never hide an unmet data dependency behind a plausible-looking but
    ungrounded implementation.**
13. Remaining `policies/` — fairness-residual/fairness_margin/anchor_favorable/
    empirical_correction for bargaining and negotiation's determined cells,
    babbling/reputation for persuasion (§4's locked deviations).
14. `opponent_models/`, `Δ_instance` logic per the boundary rules in §5.3.
15. `research/` harness and experiment registry (§7.3): run offline analysis across all
    cells, compute priority scores (§8).
16. Run live-game experiments (respecting the API's family-only matchmaking) for whichever
    cells are prioritized; apply within-cell promotion (§7.1) and same-cell confirmation
    (§7.2) — there is no cross-cell step, per §7.2's correction.
17. `communication/neutral.py`.
18. Assemble the research agents (IBO, EG-SPM per §1) using steps above plus
    `communication/neutral.py`.
19. `communication/strategic.py` and `Δ_communication` (leaderboard only, §1's
    hard constraint that it never changes the underlying economic action).
20. `leaderboard/agent.py` and `policy_router.py` — assembles the full formula from §1,
    implements the policy map (§7.2), wired to the API client.
21. Run unit/integration/smoke tests; produce the completion report (below).

### Required documentation

```
docs/
├── architecture.md          — research vs. leaderboard, policy layers, dependency
│                               boundaries (§2's import rules), promotion flow
├── theory_baselines.md      — the full configuration-specific baseline table (§4),
│                               every theoretical/approximation label, and the ROBUST
│                               v1 minimax-regret formulation with the degeneracy
│                               finding (§5.1)
├── eprocess_math.md         — the verified e-process construction (§6.2's checklist
│                               and both derivations), reproduced in full, not merely
│                               referenced
├── experiment_registry.md   — per §7.3's schema
└── verification_log.md      — per §10's entry format
```

### Completion report

At the end of the build, produce a concise report covering: files/directories created;
tests run and results; VERIFY-FIRST outcomes (§10); dataset inspection/profiling results;
which negotiation cells were successfully ingested and which are BAYES-eligible (§5.2);
which cells/components are BLOCKED and why; the exact ROBUST v1 formulation implemented;
the exact e-process formula and λ-set implemented (confirming it matches §6.2, since no
substitution was authorized); and remaining work before a real leaderboard deployment. Use
explicit status labels — `IMPLEMENTED`, `VERIFIED`, `BLOCKED`, `NOT YET BUILT` — rather
than implying completeness for anything not actually finished or verified.

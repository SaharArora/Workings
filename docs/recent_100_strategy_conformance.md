# Recent 100-game strategy-conformance audit

## Executive finding

The agent is executing the policies it was assigned, but two of the assigned policy
families are intentionally static and the current leaderboard communication layer is
not meaningfully strategic.

This audit replayed every one of our 2,715 logged decision states in the latest 100
completed games from each family at the frozen cutoffs below. The replay regenerated
the action from the recorded state, valid-action schema, assigned policy, and frozen
artifacts. All 2,715 submitted structured actions matched the regenerated policy action.

The user's behavioral observation is nevertheless substantially correct:

| Claim | Finding |
|---|---|
| The live code is failing to execute the selected policy | **Refuted:** 0 mismatches in 2,715 decision-state replays |
| Negotiation repeatedly uses one unchanged own price | **Verified:** all 49 negotiation games with at least two of our numeric offers kept one price |
| Negotiation merely copies the opponent's price | **Refuted:** 0 of 276 submitted counteroffers equaled the current opponent offer |
| Negotiation fails to react when the opponent changes price | **Verified:** the opponent changed price in 41 multi-counter games; our price changed in 0 of them |
| The optional language repeats | **Verified:** it is produced by deterministic templates, not by history-aware language generation |
| Persuasion repeats the same action each round | **Verified:** all 100 sampled games used one unchanged economic action on every one of our turns |
| The repetition is inconsistent with the declared theory | **Mostly refuted:** static negotiation ROBUST and persuasion P0 babbling are defined to behave this way |
| The behavior is strategically adequate for leaderboard play | **Not established:** the sample exposes a real adaptation and communication gap |

The crucial distinction is therefore:

```text
execution bug: no evidence in this sample
policy/communication limitation: strong evidence in this sample
```

No live policy, threshold, assignment, or runner was changed during this audit.

## Frozen sample and method

The sample is the last 100 rows by `outcomes.completed_at` for each family at a fixed
cutoff. Later live games do not alter these results.

| Family | Completion window (UTC) | Earliest / latest game | Our logged decision states |
|---|---|---|---:|
| Bargaining | 2026-08-23 16:03:23.614929 to 18:00:05.933097 | `88df168d-afac-498d-88ac-5799327c0774` / `f7ea4edd-586a-420e-be38-ef64c6526dc3` | 369 |
| Negotiation | 2026-08-23 16:31:55.092652 to 17:58:33.743393 | `ef78b150-5f44-4c15-8346-f6f221e1803f` / `a29a6927-a2f1-4ecd-b7e7-900d2abe1543` | 364 |
| Persuasion | 2026-08-23 12:32:51.903065 to 17:59:14.853972 | `cd144fe8-28b8-456a-9586-b751dad69569` / `f9f8d9bc-e437-4f4c-a3e9-c9c73e13c34d` | 1,982 |

For every game, the audit read every `policy_decision` entry, including the state,
round, accumulated history, valid actions, role, routing derivation, assigned policy,
submitted action, and optional message. It then:

1. regenerated the assigned-policy action independently;
2. regenerated the declared configuration-specific incumbent action;
3. compared structured actions with numeric tolerance only for floating-point noise;
4. grouped our offers and messages in round order;
5. compared each negotiation counter with the contemporaneous opponent offer; and
6. joined the terminal outcome and raw payoff from the evidence database.

Every sampled game had decision-level logs. The source evidence is
[`evidence.sqlite3`](../research/evaluation/cohorts/POST_RISK_FIX_RANDOMIZED_3000/evidence.sqlite3)
and the family JSONL transcripts in the same cohort directory.

### What “verified” means in this report

The report uses three evidence levels and does not treat them as interchangeable:

| Evidence level | What was checked | What it establishes |
|---|---|---|
| Live-history observation | Submitted actions, opponent actions, messages, rounds, histories, and terminal outcomes in the frozen JSONL/SQLite sample | What the deployed agent actually did |
| Independent code replay | The frozen policy function was called again on every recorded decision state and compared with the submitted structured action | Live execution conformed to the implementation |
| Formula/specification concordance | The implemented anchor's rule was compared with the formula or policy definition in `BUILD_SPEC.md` and `theory_baselines.md` | The behavior is consistent with the declared anchor, subject to the anchor's stated theoretical status |

The 2,715/2,715 result is therefore a **code-conformance** result, not an independent
proof of every game-theoretic claim. The mathematical status also differs by policy:

- complete-information bargaining uses the Rubinstein stationary formula or exact
  finite-horizon backward induction, so it has a clean mathematical anchor;
- complete-information negotiation uses the declared complete-information price rule;
- negotiation ROBUST is an explicitly specified minimax-regret operational fallback,
  not a claimed equilibrium theorem for the underdetermined cell;
- persuasion P0 is the no-commitment babbling-equilibrium anchor;
- FAIRNESS, FAIRNESS_MARGIN, ADAPTIVE, and pooled empirical policies are challengers,
  not theoretical anchors; and
- incomplete-information equal split is an explicit conservative operational incumbent
  when the prior required by the theoretical approximation is unavailable.

The pre-launch test suite checks the baseline formulas and policy invariants separately.
This 100-game audit adds live-state conformance and behavioral evidence; it does not
replace a formal derivation or theorem proof.

## Bargaining: theory changes in finite horizons, but language does not

### Sample composition and conformance

The 100 games contain 50 observational incomplete-information equal-split games, 25
randomized theory controls, and 25 randomized FAIRNESS challengers. Outcomes were 89
agreements, 7 walkaways, 3 no-deals, and 1 mechanism timeout.

All 369 actions replayed exactly. Compared with the declared incumbent:

- 314 actions (85.09%) were identical to the incumbent;
- 55 actions (14.91%), across 19 games, differed; and
- every difference was an authorized FAIRNESS offer adjustment, not an execution error.

The offer dynamics are configuration-dependent, as theory predicts. Among the 29 games
where we submitted at least two allocations, 8 changed allocation and 21 stayed fixed.
The changing sequences were concentrated in known finite-horizon complete-information
theory/FAIRNESS cells, where backward induction changes with the number of remaining
rounds. Unknown-horizon Rubinstein offers and the incomplete-information equal-split
incumbent are stationary, so their repeated allocations follow the declared policy.

Representative finite-theory trace:

- Game `c64bb3d9-d478-483d-a7e3-2a345da98038`, Bob, `T=12`, theory control.
- Our six offers changed with the shrinking horizon:
  `(12.440791, 87.559209)`, `(11.106304, 88.893696)`,
  `(9.3504, 90.6496)`, `(7.04, 92.96)`, `(4, 96)`, `(0, 100)`.
- This is the expected finite-horizon behavior, although the game ended in no deal.

Representative stationary trace:

- Game `7e0ca7a5-89c1-45cb-93b5-c80ef46c5441`, Alice, unknown horizon,
  FAIRNESS challenger.
- The agent repeated `(950000, 50000)` on 14 offer turns and ultimately walked away.
- The stationary allocation is consistent with the active unknown-horizon policy. Its
  practical effectiveness is a policy-quality question, not a routing/execution error.

### Bargaining language

There were 105 optional message-bearing offer actions. Every one used exactly:

> I propose the stated allocation.

All 17 games with multiple message-bearing offers repeated that sentence verbatim,
including games whose numeric allocation changed substantially. Bargaining economics
can therefore adapt while its language remains completely non-adaptive.

## Negotiation: the fixed price is real, reproducible, and currently by design

### Sample composition and conformance

The 100 games contain 86 observational incumbent games, 8 FAIRNESS_MARGIN challengers,
and 6 randomized theory controls. Selected-policy counts were:

| Selected policy | Games |
|---|---:|
| `NEGOTIATION_ROBUST` | 56 |
| `NEGOTIATION_INCOMPLETE_T1_ROBUST` | 22 |
| `NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT` | 8 |
| `NEGOTIATION_FAIRNESS_MARGIN` | 8 |
| `CONFIGURATION_SPECIFIC_THEORY` | 6 |

Outcomes were 36 agreements, 36 no-deals, and 28 walkaways. Across 364 decision states,
all assigned-policy actions replayed exactly. Of those actions, 360 were also identical
to the declared incumbent. The four differences occurred in four FAIRNESS_MARGIN games
and were the authorized challenger treatment.

No history-adaptive negotiation challenger was active in this window. The earlier
ADAPTIVE experiment had already safety-paused, so underdetermined cells correctly fell
back to the static ROBUST incumbent.

### Offer adaptation result

The user's main observation is verified with unusually strong consistency:

- 49 games contained at least two of our numeric offers;
- all 49 used one unchanged price throughout;
- 276 of our actions were counteroffers;
- 0/276 counters exactly equaled the opponent's current price;
- in 41 games, the opponent changed price over multiple counter rounds; and
- in 0/41 did our price change in response.

Thus the agent is not parroting the other player's price. It is holding its own fixed
reference price regardless of a changing opponent trajectory.

Seller example:

- Game `9cc319c8-6fbe-4747-8b89-5ce5849ae95e`, unknown horizon, ROBUST seller.
- Our price was `1,200,000` on 21 consecutive price-bearing actions.
- Opponent counters rose over 20 observations from `720,000` to `1,171,537.86`.
- Our quote never moved. The game eventually agreed, yielding raw seller payoff
  `400,000`.

Buyer example:

- Game `7138e969-bc28-4181-ab50-ef3795247283`, unknown horizon, ROBUST buyer.
- Our price was `40` on 12 consecutive counteroffers.
- Opponent asks moved from `171.48` to `98.37`.
- Our price never moved; the terminal outcome was walkaway and raw payoff was zero.

This is exactly what the current ROBUST definition requests. Its candidate prices and
opponent-value scenarios are fixed from the player's own value. Its ambiguity set is
not updated from history, and its acceptance rule compares the current offer with its
fixed minimax-regret proposal. The unknown-horizon guard walks away after three
*identical* offer/counter pairs. An opponent that changes its quote slightly each round
does not trigger that guard, even if the strategic situation has effectively stalled.
That exact-equality guard is a material post-cohort design risk.

### Negotiation language

There were 340 message-bearing actions. The communication layer does not inspect the
opponent's text, concessions, round, or history. It deterministically renders one of:

```text
I propose the stated price of <fixed price>.
This is my stated decision.
```

Thirty of the 48 games with multiple message-bearing actions repeated one string for
the whole game. The other 18 only alternated between the price template and decision
template; they did not generate new strategic content. The repeated language is
therefore an implementation fact, not a perception caused by a few unusual games.

## Persuasion: repetition is the P0 theory baseline, but the live deviation is also static

### Sample composition and conformance

The sample contains 93 P0 babbling games and 7 pooled-empirical seller challenger games;
52 roles were buyer and 48 seller. There were 98 normal completions and 2 mechanism
timeouts.

All 1,982 actions replayed exactly. Relative to P0:

- 1,882 actions (94.95%) were identical;
- 100 actions (5.05%), in five text-message challenger games, differed; and
- the two binary-recommendation challenger games chose the same `yes` action as P0.

Every one of the 100 games had multiple agent turns, and every game used one unchanged
economic action on all our turns.

The round-level action totals make the repetition explicit:

| Action type | Logged actions | Observed behavior |
|---|---:|---|
| Buyer decision | 1,038 | one fixed `yes` or `no` for the entire game |
| Seller binary recommendation | 520 | `yes` every round under both sampled policies |
| Seller textual message | 424 | one fixed sentence for the entire game |

For the 17 P0 text games, all 324 messages were:

> This product is available.

For the five pooled-empirical text games, all 100 messages were:

> I recommend buying this product.

For example, game `74dc041e-cbaf-466d-aa21-b36a86d01cfd` sent the latter message in all
20 rounds and earned raw seller payoff zero.

The P0 buyer repetition is theoretically coherent: the no-commitment babbling baseline
requires the buyer to ignore seller messages and buy from the same expected-value test
each round. Since the configuration values and price do not change, its answer cannot
change. The P0 seller likewise emits an uninformative constant message/recommendation.

The pooled seller challenger is nominally history-aware through its feature map, but its
action space contains only two text strings (or binary yes/no), and none of the seven
sampled games crossed a model ranking boundary that changed the chosen action. It is a
population response model, not a genuine natural-language generator.

## Does gameplay follow the strategy we intended?

There are three different answers.

### 1. Does live execution follow the selected policy implementation?

**Yes.** The replay result is 2,715/2,715 matching decision states, with no within-game
policy switches and no sampled invalid action or execution fallback.

### 2. Does it follow the declared incumbent definitions?

**Yes at the formula/specification-concordance level, with authorized experimental
deviations.** Finite bargaining changes as backward induction requires. Unknown-horizon
bargaining is stationary. Negotiation ROBUST stays static because the specification
explicitly freezes its ambiguity set; that is conformance to a declared fallback, not
proof of an equilibrium. Persuasion P0 repeats because babbling theory explicitly
ignores messages. Every observed departure from an incumbent was attributable to an
assigned FAIRNESS or pooled-empirical arm.

### 3. Does it realize a genuinely adaptive leaderboard strategy?

**No.** The repository architecture names a leaderboard-only `Delta_communication`
layer, but the current implementation is a deterministic renderer with three generic
templates. It adds legal text after the economic action but performs no strategic
language generation. The currently active negotiation and persuasion incumbents also
have no history-driven action update. Consequently, the full deployed behavior is much
closer to:

```text
configuration policy + static placeholder language
```

than to:

```text
configuration policy + instance adaptation + strategic communication
```

That is the main gap demonstrated by this audit.

## Post-cohort recommendations

These are recommendations for a separately tested change, not authorization to mutate
the frozen live cohort.

1. Keep ROBUST and P0 as auditable controls. Do not silently make them adaptive; that
   would erase the meaning of the current experiments.
2. Restore a separately named negotiation history-aware challenger after revising and
   retesting its safety objective. It should respond to concession trajectory and near-
   stagnation, then be compared against unchanged ROBUST.
3. Replace exact-pair stagnation detection with a declared, scale-aware structural guard
   in a new policy version. Tiny opponent price changes currently evade the guard.
4. Implement a real leaderboard communication treatment that conditions only language
   on role, round, offer trajectory, and opponent text while preserving the finalized
   economic action. Evaluate it separately so language is not confounded with price.
5. Give the persuasion challenger a richer, predeclared message/action set and evaluate
   a history-aware P3-style challenger against unchanged P0. The current two-message
   action space is too small to demonstrate adaptive language.
6. Add this 100-game decision replay as a repeatable post-cohort regression audit,
   including offer-change, message-diversity, and incumbent-counterfactual metrics.

## Evidence and implementation trace

- Frozen cohort ledger: [`evidence.sqlite3`](../research/evaluation/cohorts/POST_RISK_FIX_RANDOMIZED_3000/evidence.sqlite3)
- Bargaining transcript: [`bargaining.jsonl`](../research/evaluation/cohorts/POST_RISK_FIX_RANDOMIZED_3000/bargaining.jsonl)
- Negotiation transcript: [`negotiation.jsonl`](../research/evaluation/cohorts/POST_RISK_FIX_RANDOMIZED_3000/negotiation.jsonl)
- Persuasion transcript: [`persuasion.jsonl`](../research/evaluation/cohorts/POST_RISK_FIX_RANDOMIZED_3000/persuasion.jsonl)
- Static negotiation ambiguity set and exact-pair guard: [`policies/negotiation/robust.py`](../policies/negotiation/robust.py)
- Bargaining, negotiation, and persuasion incumbent actions: [`leaderboard/policy_router.py`](../leaderboard/policy_router.py)
- Deterministic language templates: [`communication/strategic.py`](../communication/strategic.py)
- Declared baseline semantics: [`theory_baselines.md`](theory_baselines.md)
- Authoritative architecture/specification: [`BUILD_SPEC.md`](BUILD_SPEC.md)

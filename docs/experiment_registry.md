# Experiment registry

No e-process promotion experiment has completed. Human-authorized bounded pilots are
tracked separately and never make a policy leaderboard-eligible; eligibility still
requires a completed promotion and confirmation entry here.

## Required fields

`experiment_id`, `cell`, `opponent_category`, `incumbent`, `candidate`, `model_version`,
`alpha_family`, `M`, `alpha_test`, `delta_min`, `data_window`, `n_games`, `E_t_final`,
`E_t_prime_final`, `effect_estimate`, `raw_payoff_effect`, `payoff_transform_version`,
`clipping_count`, `clipping_rate`, `outcome`, `active_policy`, and `code_commit`.

For negotiation, `effect_estimate` is the candidate-minus-incumbent mean difference in
the clipped scale-adjusted score `Y`. `raw_payoff_effect` is always reported alongside it
as a diagnostic; it is not the bounded e-process input. The locked transform version is
`negotiation_clipped_utility_score_v1`.

## Candidate inventory (not promotion records)

Every incomplete candidate below is `RESEARCH_BLOCKED`, not a
`DEPLOYMENT_BLOCKER`: the coverage matrix records a separate intentional executable
incumbent for every reachable cell. These statuses do not authorize promotion.

The following implemented candidates remain **not leaderboard-eligible** until a completed
experiment row with all required fields records promotion and same-cell confirmation:

| Family/cell | Incumbent | Candidate | Status |
|---|---|---|---|
| Bargaining/all | cell incumbent | fairness-0.10 | HUMAN_AUTHORIZED_EXPERIMENTAL for bounded 4-game pilot; not promoted |
| Negotiation/complete finite | cell theory | fairness-margin-0.15 | HUMAN_AUTHORIZED_EXPERIMENTAL for bounded 6-game family pilot when matched; not promoted |
| Negotiation/complete unlimited | midpoint | own-favorable-0.65 | NOT_YET_BUILT + RESEARCH_BLOCKED: not tested/promoted |
| Negotiation/incomplete T=1 | current ROBUST | empirical correction | NOT_YET_BUILT + RESEARCH_BLOCKED: no trusted prior/promotion |
| Negotiation/incomplete T=1 | current ROBUST | NEGOTIATION_ADAPTIVE | HUMAN_AUTHORIZED_EXPERIMENTAL for bounded 6-game family pilot; first/terminal rules reduce to ROBUST reference/IR behavior |
| Negotiation/incomplete multi-round | ROBUST (current data gate) | NEGOTIATION_ADAPTIVE | HUMAN_AUTHORIZED_EXPERIMENTAL for bounded 6-game family pilot; not promoted |
| Negotiation/incomplete multi-round/unknown horizon | ROBUST | BAYES | RESEARCH_BLOCKED where no exact-cell artifact passes its separate support gate |
| Negotiation/incomplete multi-round/unknown horizon with supported public features | ROBUST | NEGOTIATION_POOLED_EMPIRICAL / RISK_SENSITIVE_POOLED_EMPIRICAL | `PAUSED_FOR_COMPETITION_CYCLE`; 0/36 risk-grid combinations passed coverage + endpoint sanity; no live test or promotion |
| Persuasion/repeated | P0 babbling | P3 reputation | P3_EXPERIMENT_INPUT_UNAVAILABLE + RESEARCH_BLOCKED: historical cell trust rate unavailable; P0 remains selected |
| Persuasion/seller message choice | P0 babbling | PERSUASION_POOLED_EMPIRICAL | OFFLINE IMPLEMENTED; held-out BSS 0.6318; not live-authorized or promoted and does not provide P3 inputs |

## Pooled population offline record (not promotion evidence)

The negotiation pooled dataset is derived from original public GLEE data at source commit
`68a33e98b035b97f945badee8f325001555c0049`: 33,627 games and 96,214 pre-response rows,
split deterministically by whole game into 20,161/6,726/6,740 train/validation/test games
(57,675/19,218/19,321 rows). The role-specific regularized logistic response model
achieves test Brier 0.1764, BSS 0.1719 against the declared global-rate baseline, log loss
0.5303, acceptance prevalence 0.3076, and calibration ECE 0.0237. Its BSS against the
stronger structural-group baseline is 0.1536.

This pooled model intentionally does not require an exact structural cell to have 200
observations. That old gate continues to govern only the distinct exact-cell BAYES path.
The pooled model passed predictive-skill, calibration, leakage, IR, candidate-generation,
latency, and non-cloning checks, but failed the additional economic-sanity review: its
held-out selected actions were more agreement-oriented than ROBUST in 0.0% of seller rows
and 1.0% of buyer rows. The authorized ten-game validation tranche therefore did not run,
no rating changed, and no e-process evidence was created.

The continuation-aware follow-up froze the model and evaluated all 36 predeclared
`lambda/alpha/epsilon` combinations on 4,031 whole games / 11,591 supported decisions.
This was fresh to selector tuning but not independent of response fitting: every public
game had already been consumed by response train/calibration/test, and public HEAD still
matched source commit `68a33e98...`. Only 2,819 decisions had any candidate satisfying
the explicit `P(raw Q<=0)<=0.50` constraint. Seller endpoint rate remained 0.8192 among
selected states (old 0.9959), exceeding the predeclared 0.25 ceiling; buyer improved to
0.1493. No combination passed, no parameters were selected, and the validation registry
now fails closed with `POOLED_EMPIRICAL_PAUSED_COMPETITION_CYCLE_RISK_SELECTOR_FAILED`.
This is not e-process evidence.

The separate persuasion pooled dataset contains 13,506 public games and 270,120 buyer
decisions. Its seller-side message response model achieves held-out Brier 0.0919, BSS
0.6318, log loss 0.3084, and ECE 0.0209. It remains an offline challenger: it does not
replace the buyer safety margin, fabricate quality information, or satisfy P3's missing
population-trust input.

## Time-constrained leaderboard tranche authorization (not promotion)

The frozen precommitment is `docs/leaderboard_tranche_plan.md`: bargaining FAIRNESS for
20 family games, negotiation FAIRNESS_MARGIN in applicable complete cells plus at most six
eligible ADAPTIVE diagnostic selections within 20 family games, and persuasion P0 for 12
family games. Challenger labels remain `HUMAN_AUTHORIZED_EXPERIMENTAL` or
`HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC`; none is relabeled
`E_PROCESS_PROMOTED`.

The ADAPTIVE allocation is not entered as a formal randomized experiment. Although the
pure seeded `Experiment.assign()` primitive is implemented and tested, no live
cell-matched router currently binds its pre-outcome assignment/order log to bounded game
lifecycle and outcome observation. The tranche therefore uses a plainly logged
first-eligible diagnostic assignment instead of improvising a causal design. Its results
remain descriptive and do not update this promotion registry.

## Human-authorized bounded pilot record (not promotion evidence)

Frozen commit: `c4e68a569376c178b8844db6594c5ced92fd9f3b`. Assignment came from
ordinary family matchmaking, not randomized theory/challenger assignment within exact
cells. These rows are descriptive operational/policy evidence and must not enter an
e-process or authorize promotion.

| Family | Requested/completed | Experimental selections | Outcomes/payoffs | Raw rating | Operational status | Promotion status |
|---|---:|---|---|---|---|---|
| Negotiation | 6/6 | ADAPTIVE 4; FAIRNESS_MARGIN 2 | ADAPTIVE: 1 agreement (55.24), 2 no-deals (0), 1 walkaway (0); fairness: 2 agreements (3, 1960) | 974.79 -> 976.73 | zero hard stops/fallbacks/invalid/timeouts/strategic events | HUMAN_AUTHORIZED_EXPERIMENTAL; NOT PROMOTED |
| Bargaining | 4/4 | FAIRNESS 4 | 4 agreements; payoffs 5156.4, 5000, 580943.09, 95 | 1670.46 -> 1693.53 | zero hard stops/fallbacks/invalid/timeouts/strategic events | HUMAN_AUTHORIZED_EXPERIMENTAL; NOT PROMOTED |
| Persuasion | 4/4 | P3 selected 0; P0 control 4 | P0 seller payoffs 0, 2000, 20000000; buyer payoff 0 | 1402.31 -> 1406.98 | P3 input unavailable on all 60 seller turns; zero operational/strategic events | P3_EXPERIMENT_INPUT_UNAVAILABLE; NOT PROMOTED |

## Time-constrained tranche record (not promotion evidence)

Frozen commit: `9fcae232ea1f6f474ad5382c0936bd1f1a0a5b4d`. This was a
nonrandom deployment tranche governed by `docs/leaderboard_tranche_plan.md`, not an
e-process experiment. Its outcomes must not enter promotion evidence.

| Family | Requested/completed | Manually authorized selections | Rating | Operational status | Strategic result | Deployment classification |
| --- | ---: | --- | --- | --- | --- | --- |
| Bargaining | 20/20 | FAIRNESS 11; safe/theory incumbents 9 after pauses | 1693.53 -> 1712.58 | zero hard stops/fallbacks/invalid/timeouts; exact bounded exit | incomplete FAIRNESS and complete finite FAIRNESS paused | PAUSE_AND_REDESIGN |
| Negotiation | 20/6 | ADAPTIVE 2; ROBUST 3; complete unlimited midpoint 1 | 976.73 -> 969.14 | zero hard stops/fallbacks/invalid/timeouts; strategic stop with clean drain | both ADAPTIVE classes paused; unknown-horizon ROBUST first three all zero | PAUSE_AND_REDESIGN |
| Persuasion | 12/5 | P0 5; P3 0 | 1406.98 -> 1383.34 | zero hard stops/fallbacks/invalid/timeouts; strategic stop with clean drain | seller P0 zero-payoff rate 2/3 | PAUSE_AND_REDESIGN |

The samples remain descriptive. No challenger or incumbent is relabeled
`E_PROCESS_PROMOTED`, and no sustained deployment was started.

## Post-risk-fix cohort registry (registered, not yet launched)

The frozen precommitment is `docs/post_risk_fix_cohort_plan.md`; its registry hash is
`fd045b13c86e9071bfd0ee1fbfb458e7d6594b0bca4053022a3169e4fb383a52` and is persisted
before the first assignment.
All five exploration experiments are `RUNNING` only inside a newly initialized
`POST_RISK_FIX_RANDOMIZED_3000` evidence store. At repository freeze they are
`REGISTERED_PENDING_LAUNCH`, with zero assignments and zero e-process observations.
Five matching `CONFIRM_...` rows are predeclared `NOT_STARTED`, use fresh data with
`M=1`/threshold 20, and activate only when the corresponding exploration becomes a
`PROMOTION_CANDIDATE`. Exploration observations are never copied into confirmation.

| Experiment | Eligible structural regime | Incumbent | Challenger | alpha test / threshold | Status |
|---|---|---|---|---:|---|
| `NEG_INCOMPLETE_IBO_VS_ROBUST` | incomplete multi-round/unknown negotiation | ROBUST | ADAPTIVE v1 | .025 / 40 | REGISTERED_PENDING_LAUNCH |
| `NEG_COMPLETE_FAIRNESS_MARGIN_VS_THEORY` | complete finite gains-from-trade negotiation | exact cell theory | fairness 0.15 | .025 / 40 | REGISTERED_PENDING_LAUNCH |
| `BARG_COMPLETE_FAIRNESS_VS_THEORY` | complete bargaining with verified inputs | exact cell theory | fairness 0.10 | .05 / 20 | REGISTERED_PENDING_LAUNCH |
| `PERS_BUY_MARGIN_VS_THEORY` | buyer states with EV inputs | exact weak EV threshold | 2% margin | .025 / 40 | REGISTERED_PENDING_LAUNCH |
| `PERS_SELL_EMPIRICAL_VS_P0` | seller states with all pooled features | P0 | pooled empirical v1, not P3 | .025 / 40 | REGISTERED_PENDING_LAUNCH |

Every exploration row above has a confirmation row named
`CONFIRM_<exploration experiment ID>`, with identical eligibility/control/challenger,
`alpha_test=.05`, and promotion threshold 20. A promotion record requires the
confirmation row—not exploration alone—to reach its statistical and practical-effect
gates. If the family cap arrives first, the exploration remains
`PROMOTION_PENDING_CONFIRMATION` and no policy is promoted.

`NEG_INCOMPLETE_T1` and `BARG_INCOMPLETE_IBO_VS_STATIC` remain observational because no
valid challenger was implemented before freeze. Negotiation pooled/risk-sensitive
empirical selectors and persuasion P3 remain inactive. No pre-fix game may update these
trajectories.

## Preserved pre-fix cohorts

`PRE_RISK_FIX_BARGAINING_200` contains exactly 200 tracked bargaining games from commits
`fa6a60e...` and `ea14b49...`: 199 complete terminal traces and one missing terminal
trace. All 200 are `OBSERVATIONAL_LIVE_EVIDENCE`; 111 used bargaining fairness and 89
used the incomplete equal-split incumbent. Per-game records and source hashes are under
`research/evaluation/cohorts/`.

The four negotiation games started during the interrupted pre-fix launch are separately
identified as `PRE_RISK_FIX_NEGOTIATION_INTERRUPT_4`. They are observational, have four
complete traces, and do not count toward the new 1,000-game negotiation cap.

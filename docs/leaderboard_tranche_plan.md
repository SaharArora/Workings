# Time-constrained leaderboard tranche: frozen precommitment

This document is the pre-queue policy map and stop-loss manifest for one bounded rated
tranche. The commit containing it is the frozen tranche commit. Policies and thresholds
must not change after the first tranche game; a required code change stops the affected
family and is reported instead.

## Authorization boundary

- Bargaining: 20 games.
- Negotiation: 20 games, including at most six distinct eligible games assigned to the
  ADAPTIVE diagnostic.
- Persuasion: 12 games.
- Concurrency is one. The authoritative bounded supervisor alone performs controlled
  queue top-ups, never tracks more than the family cap, and always leaves all queues.
- No repeated queueing to manufacture configurations. No sustained deployment follows
  automatically.

All challenger use remains manually authorized. It is not formal e-process promotion,
causal proof, Bayes optimality, or population optimality. The recent FAIRNESS bargaining
sample (n=4), FAIRNESS_MARGIN negotiation sample (n=2), and ADAPTIVE negotiation sample
(n=4) are only consistent with their design hypotheses under small live samples.

## Acceptance-rule audit

`STATIC_ROBUST_OLD_ACCEPTANCE_RULE_ACTIVE = yes`

Static `NEGOTIATION_ROBUST` still accepts a nonterminal offer only when it is individually
rational and at least as favorable as its fixed minimax-regret proposal. That rule was
introduced during implementation rather than required by `BUILD_SPEC.md`. It is retained
unchanged here as the static conservative control; this task found no correctness bug in
its implementation.

`ADAPTIVE_OLD_ACCEPTANCE_RULE_ACTIVE = no`

`NEGOTIATION_ADAPTIVE` accepts any individually rational terminal offer. With legal
continuation it accepts only when current payoff is at least 0.90 times the adaptive
continuation-target payoff; otherwise it rejects and makes the adaptive counter when
legal. Tests exercise a state that static ROBUST rejects but ADAPTIVE accepts under this
different rule.

## Frozen production policy map

| Family / reachable class | Control/reference | Live tranche selection | Authorization / unavailable behavior |
| --- | --- | --- | --- |
| Bargaining where FAIRNESS is defined | configuration-specific theory, or the named safe incumbent if theory inputs are unavailable | `BARGAINING_FAIRNESS`, with `FAIRNESS_CONCESSION=0.10` | `HUMAN_AUTHORIZED_EXPERIMENTAL`; if the challenger is paused/undefined, retain the safe incumbent and log the reason |
| Negotiation, complete-information finite extraction, including T=1 | exact theory; T=1 remains seller `p=V_B` under accept-at-indifference | `NEGOTIATION_FAIRNESS_MARGIN`, with `SURPLUS_CONCESSION=0.15` | `HUMAN_AUTHORIZED_EXPERIMENTAL` |
| Negotiation, complete-information unknown horizon | configuration theory incumbent | configuration theory incumbent | theory/portfolio status unchanged |
| Negotiation, incomplete-information T=1 with trusted prior | one-shot theoretical Bayes posted price | same incumbent | not routed through the multi-round BAYES gate or ADAPTIVE |
| Negotiation, incomplete-information T=1 without trusted prior | one-shot ROBUST | same incumbent | not routed through ADAPTIVE |
| Negotiation, incomplete-information multi-round/unknown horizon | genuinely promoted policy; else eligible loadable BAYES artifact; else ROBUST | incumbent by default; first at most six distinct eligible arriving games may use ADAPTIVE | ADAPTIVE is `HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC`; cap/stop-loss returns future games to the incumbent |
| Persuasion, buyer or seller | P0 | P0 | P3 remains `RESEARCH_BLOCKED`; no population purchase-rate input is fabricated |

The exact complete-information T=1 theorem has not been changed to `V_B-epsilon`. Real
competition opponents need not accept at exact indifference. The exact theoretical
solution remains the control, while the human-authorized fairness-margin policy is the
production challenger during this tranche.

The live experiment setup command can configure the tested `Experiment` assignment
primitive, but the repository does not contain a live cell-matched randomized router that
binds its pre-outcome assignments to this bounded supervisor. Therefore this tranche does
not improvise a pseudo-random experiment. ADAPTIVE assignment is a plainly logged,
nonrandom diagnostic: first eligible distinct games up to the six-game challenger cap.

## Scale-adjusted monitoring

- Every family retains raw own payoff.
- Bargaining also records `own_payoff / money_to_divide` and, when our terminal proposal
  supplies a valid same-state theory reference, its discounted normalized theory payoff.
- Negotiation also records the locked bounded statistical transformed payoff `Y` and all
  clipping metadata. This is not mechanism normalization; legal price is unbounded above.
- Persuasion keeps existing configuration-appropriate evaluation only. No new transform is
  fabricated for this tranche.
- Rating changes are descriptive only.

Exact cells and these scale-invariant structural classes are both logged: bargaining
FAIRNESS by complete finite, complete unlimited, or incomplete; negotiation
FAIRNESS_MARGIN by complete T1/finite and ROBUST/ADAPTIVE by incomplete multiround or
unknown horizon; persuasion P0 by buyer/seller.

## Predeclared stop-losses

Immediate operational family stop: invalid submitted action; production-policy execution
fallback; outer never-raise fallback; unsupported reachable cell; run-control failure;
uncontrolled extra game; credential exposure; action-time safety violation; or a
deterministic cycle that escapes its intended guard. Transient API polling errors continue
only through the existing bounded retry behavior. Cleanup always leaves all queues.

At a structural policy class with n>=3, pause that class when more than half of outcomes
are zero-payoff/no-deal/walkaway and at least one such failure is not explicitly marked by
the mechanism as mechanically unavoidable. Also pause when the first three observations
all give zero own payoff. With no explicit terminal unavoidability indicator, an observed
failure is conservatively treated as not proven mechanically unavoidable.

Additional locked rules:

- ADAPTIVE: after at least three diagnostic games, pause on zero agreement rate; also
  pause after two logged instances of ignoring a materially improving offer.
- FAIRNESS_MARGIN: after at least three applicable games, pause above 50% zero payoff.
- BARGAINING_FAIRNESS: after five applicable games, pause below 50% agreement, or when at
  least four valid same-state comparisons in the first five have normalized payoff no
  greater than the discounted theory reference.
- Rating decline alone never triggers a stop.

A paused challenger class reverts only future games to its frozen incumbent. An already
assigned game keeps one policy for its complete lifecycle. If the stopped class is itself
an incumbent with no defined alternative, the bounded family run stops rather than invent
a strategy.

## Post-tranche decision rule

For each family, `SUSTAINED_DEPLOYMENT_ELIGIBLE` requires: no operational stop; no active
production structural class stop-loss; intentional incumbents for every encountered cell;
and safe latency. Statistical superiority is not required. Operationally sound but mixed
families are `LIMITED_DEPLOYMENT_ONLY`. Any operational stop or triggered structural-class
stop-loss is `PAUSE_AND_REDESIGN`. ADAPTIVE defaults to `LIMITED_DEPLOYMENT_ONLY` absent a
clearly favorable diagnostic result and never becomes e-process promoted here.

Even if eligible, sustained execution is not started. Every queue is shut down and the
system waits for explicit human authorization.

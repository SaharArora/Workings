# Behavioral challenger bounded-pilot report

## 1. Frozen commit SHA

`c4e68a569376c178b8844db6594c5ced92fd9f3b`. No policy or threshold changed during the 6/4/4 pilot.

## 2. Full test result

`223 passed` on the frozen merge commit before rated execution; the same full suite passed again during report-only release verification.

## 3. Provenance of the old ROBUST acceptance rule

The fixed-quote acceptance threshold was introduced by implementation commit `7ced172`; `docs/BUILD_SPEC.md` locks ROBUST's static ambiguity/minimax-regret proposal but does not specify that response threshold. Static ROBUST remains unchanged as the control.

## 4. NEGOTIATION_ADAPTIVE definition

Starts at ROBUST's quote, conditions only on observed offers, uses the locked 0.35 reciprocal concession and 0.90 continuation-target acceptance fraction, and uses a structural relative-tolerance cycle guard. It is deterministic, model-light, and not BAYES.

## 5. Complete-information theory versus fairness margin

Theory remains exact extraction (`V_B` in T=1 under accept-at-indifference). The bounded challenger gives the responder exactly 15% of gains from trade.

## 6. Bargaining theory versus fairness

Theory remains the configuration incumbent. The challenger maps proposer share `x` to `x - 0.10*(x-0.5)`; every live decision logs theory, adjusted, and selected offers.

## 7. Persuasion P3 input audit

No valid frozen population-positive-purchase-rate input exists. P3 was not activated; seller-side P0 remained selected with `P3_EXPERIMENT_INPUT_UNAVAILABLE`.

## 8. Experimental override registry

```json
{
  "authorization_source": "human_authorized_bounded_pilot",
  "enabled": true,
  "overrides": [
    {
      "baseline_policies": [
        "NEGOTIATION_COMPLETE_FINITE_EVEN_THEORY",
        "NEGOTIATION_COMPLETE_FINITE_ODD_THEORY",
        "NEGOTIATION_COMPLETE_T1_THEORY"
      ],
      "configuration_scope": "complete_information_and_finite_full_extraction_baseline",
      "game_family": "negotiation",
      "policy_name": "NEGOTIATION_FAIRNESS_MARGIN",
      "seller_only": false
    },
    {
      "baseline_policies": [
        "NEGOTIATION_INCOMPLETE_T1_ROBUST",
        "NEGOTIATION_ROBUST"
      ],
      "configuration_scope": "incomplete_information_cells_with_static_robust_control",
      "game_family": "negotiation",
      "policy_name": "NEGOTIATION_ADAPTIVE",
      "seller_only": false
    },
    {
      "baseline_policies": [],
      "configuration_scope": "all_reachable_bargaining_cells",
      "game_family": "bargaining",
      "policy_name": "BARGAINING_FAIRNESS",
      "seller_only": false
    },
    {
      "baseline_policies": [
        "PERSUASION_P0_BABBLING"
      ],
      "configuration_scope": "repeated_persuasion_seller_side",
      "game_family": "persuasion",
      "policy_name": "PERSUASION_P3_REPUTATION",
      "seller_only": true
    }
  ],
  "population_positive_purchase_rate_available": false
}
```

## 9. Negotiation pilot game-by-game results

| # | Game | Configuration | Role / opponent | Baseline | Experimental | Authorization | Selected | Structured actions | Outcome | Raw payoff | Scale-adjusted | Rating before -> after |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | `4d577ccf-6dab-4bb8-8878-34217f0597ce` | `{"complete_information":false,"horizon_known":true,"max_rounds":10,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":15000.0}` | buyer / agent:champion | `NEGOTIATION_ROBUST` | `NEGOTIATION_ADAPTIVE` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `NEGOTIATION_ADAPTIVE` | `{"decision":"RejectOffer","message":"I propose the stated price of 7500.0.","product_price":7500.0}`; 4x `{"decision":"RejectOffer","message":"I propose the stated price of 8946.2455.","product_price":8946.2455}` | no_deal | 0 | 0.5 | 974.79 -> 970.06 |
| 2 | `098694b1-e1bb-430e-8719-69330eadcba5` | `{"complete_information":true,"horizon_known":true,"max_rounds":10,"messages_allowed":true,"player_1_role":"seller","player_1_value":120.0,"player_2_role":"buyer","player_2_value":150.0}` | buyer / hidden:None | `NEGOTIATION_COMPLETE_FINITE_EVEN_THEORY` | `NEGOTIATION_FAIRNESS_MARGIN` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `NEGOTIATION_FAIRNESS_MARGIN` | `{"decision":"AcceptOffer","message":"This is my stated decision."}` | agreement | 3.0 | 0.505 | 970.06 -> 965.86 |
| 3 | `ff4ac28a-f264-475e-9544-c9b1a2848d15` | `{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_1_value":1500000.0,"player_2_role":"buyer"}` | seller / agent:champion | `NEGOTIATION_INCOMPLETE_T1_ROBUST` | `NEGOTIATION_ADAPTIVE` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `NEGOTIATION_ADAPTIVE` | `{"message":"I propose the stated price of 2250000.0.","product_price":2250000.0}` | no_deal | 0 | 0.5 | 965.86 -> 967.5 |
| 4 | `a2ddadec-3c10-4652-b161-4c4c935f209d` | `{"complete_information":false,"horizon_known":true,"max_rounds":10,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":150.0}` | buyer / agent:champion | `NEGOTIATION_ROBUST` | `NEGOTIATION_ADAPTIVE` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `NEGOTIATION_ADAPTIVE` | `{"decision":"RejectOffer","message":"I propose the stated price of 77.485.","product_price":77.485}`; `{"decision":"AcceptOffer","message":"This is my stated decision."}` | agreement | 55.24 | 0.5920666666666666 | 967.5 -> 974.73 |
| 5 | `27b69e5b-26f3-4d2f-a8f9-ecfc1324f19c` | `{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_2_role":"buyer","player_2_value":8000.0}` | buyer / agent:champion | `NEGOTIATION_ROBUST` | `NEGOTIATION_ADAPTIVE` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `NEGOTIATION_ADAPTIVE` | `{"decision":"RejectOffer","message":"I propose the stated price of 4000.0.","product_price":4000.0}`; 2x `{"decision":"RejectOffer","message":"I propose the stated price of 4362.257.","product_price":4362.257}`; `{"decision":"WalkAway","message":"This is my stated decision."}` | walked_away | 0 | 0.5 | 974.73 -> 972.98 |
| 6 | `0780b1a6-edab-4d2f-8fc6-c2ba75a04987` | `{"complete_information":true,"horizon_known":true,"max_rounds":1,"messages_allowed":false,"player_1_role":"seller","player_1_value":8000.0,"player_2_role":"buyer","player_2_value":15000.0}` | buyer / agent:champion | `NEGOTIATION_COMPLETE_T1_THEORY` | `NEGOTIATION_FAIRNESS_MARGIN` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `NEGOTIATION_FAIRNESS_MARGIN` | `{"decision":"AcceptOffer","message":"This is my stated decision."}` | agreement | 1960.0 | 0.5326666666666666 | 972.98 -> 976.73 |

## 10. Bargaining pilot game-by-game results

| # | Game | Configuration | Role / opponent | Baseline | Experimental | Authorization | Selected | Structured actions | Outcome | Raw payoff | Scale-adjusted | Rating before -> after |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | `4e3688cb-6045-4406-9354-f7960373d960` | `{"complete_information":true,"delta_1":0.8,"delta_2":0.8,"horizon_known":true,"max_rounds":12,"messages_allowed":false,"money_to_divide":10000}` | alice / agent:Mew | `BARGAINING_COMPLETE_FINITE` | `BARGAINING_FAIRNESS` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"alice_gain":5156.402616320001,"bob_gain":4843.597383679999}` | agreement | 5156.4 | 0.51564 | 1670.46 -> 1672.6 |
| 2 | `538f168c-77b6-4e10-92ec-17fb99a5b673` | `{"complete_information":false,"delta_1":0.9,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":10000}` | alice / agent:chotu | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `BARGAINING_FAIRNESS` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"alice_gain":5000.0,"bob_gain":5000.0,"message":"I propose the stated allocation."}` | agreement | 5000.0 | 0.5 | 1672.6 -> 1679.0 |
| 3 | `1f116516-475e-4206-a04d-b7182657f70a` | `{"complete_information":true,"delta_1":0.95,"delta_2":0.95,"horizon_known":false,"messages_allowed":true,"money_to_divide":1000000}` | alice / agent:pas-2 | `BARGAINING_COMPLETE_UNLIMITED` | `BARGAINING_FAIRNESS` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"alice_gain":511538.46153846185,"bob_gain":488461.53846153815,"message":"I propose the stated allocation."}`; `{"decision":"accept"}` | agreement | 580943.09 | 0.58094309 | 1679.0 -> 1686.99 |
| 4 | `4f58c582-485d-4491-b15e-877c58d9bb2f` | `{"complete_information":true,"delta_1":0.8,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":false,"money_to_divide":100}` | bob / agent:Quagsire | `BARGAINING_COMPLETE_FINITE` | `BARGAINING_FAIRNESS` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"decision":"reject"}`; `{"alice_gain":5.000000000000004,"bob_gain":95.0}`; `{"decision":"reject"}`; `{"alice_gain":5.000000000000004,"bob_gain":95.0}`; `{"decision":"reject"}`; `{"alice_gain":5.000000000000004,"bob_gain":95.0}`; `{"decision":"reject"}`; `{"alice_gain":5.000000000000004,"bob_gain":95.0}`; `{"decision":"reject"}`; `{"alice_gain":5.000000000000004,"bob_gain":95.0}`; `{"decision":"reject"}`; `{"alice_gain":5.000000000000004,"bob_gain":95.0}` | agreement | 95.0 | 0.95 | 1686.99 -> 1693.53 |

## 11. Persuasion pilot game-by-game results

| # | Game | Configuration | Role / opponent | Baseline | Experimental | Authorization | Selected | Structured actions | Outcome | Raw payoff | Scale-adjusted | Rating before -> after |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | `ef7dc0a7-e95e-4896-b6cf-7859aafb7060` | `{"is_seller_know_cv":false,"p":0.3333333333333333,"product_price":10000,"seller_message_type":"binary","total_rounds":20}` | seller / hidden:None | `PERSUASION_P0_BABBLING` | `PERSUASION_P3_REPUTATION` | `THEORY_INCUMBENT` | `PERSUASION_P0_BABBLING` | 20x `{"decision":"yes"}` | completed | 0.0 | None | 1402.31 -> 1395.98 |
| 2 | `49c2c342-f584-43e9-ad50-38df1e98f768` | `{"is_seller_know_cv":true,"p":0.3333333333333333,"product_price":100,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":400.0}` | seller / hidden:None | `PERSUASION_P0_BABBLING` | `PERSUASION_P3_REPUTATION` | `THEORY_INCUMBENT` | `PERSUASION_P0_BABBLING` | 20x `{"message":"This product is available."}` | completed | 2000.0 | None | 1395.98 -> 1401.33 |
| 3 | `03c1e09c-20bd-4fa7-be99-10a22857a91b` | `{"is_seller_know_cv":true,"p":0.5,"product_price":100,"seller_message_type":"binary","total_rounds":20,"u":0.0,"v":125.0}` | buyer / hidden:None | `PERSUASION_P0_BABBLING` | `None` | `THEORY_INCUMBENT` | `PERSUASION_P0_BABBLING` | 20x `{"decision":"no"}` | completed | 0.0 | None | 1401.33 -> 1399.92 |
| 4 | `ccb5b42f-9d21-4291-9b4b-2998f6c87578` | `{"is_seller_know_cv":false,"p":0.5,"product_price":1000000,"seller_message_type":"binary","total_rounds":20}` | seller / agent:theta | `PERSUASION_P0_BABBLING` | `PERSUASION_P3_REPUTATION` | `THEORY_INCUMBENT` | `PERSUASION_P0_BABBLING` | 20x `{"decision":"yes"}` | completed | 20000000.0 | None | 1399.92 -> 1406.98 |

## 12. Structural policy-class aggregates

| Structural policy class | n | Agreements | No-deals | Walkaways | Raw payoff | Scale-adjusted payoff | Rating delta | Selected policies | Opponent categories |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | --- | --- |
| `bargaining/complete-info/finite-horizon/alice/BARGAINING_FAIRNESS` | 1 | 1 | 0 | 0 | mean=5156.4, min=5156.4, max=5156.4 | mean=0.51564, min=0.51564, max=0.51564 | 2.1399999999998727 | `{"BARGAINING_FAIRNESS":1}` | `{"agent":1}` |
| `bargaining/complete-info/finite-horizon/bob/BARGAINING_FAIRNESS` | 1 | 1 | 0 | 0 | mean=95, min=95, max=95 | mean=0.95, min=0.95, max=0.95 | 6.539999999999964 | `{"BARGAINING_FAIRNESS":1}` | `{"agent":1}` |
| `bargaining/complete-info/unknown-horizon/alice/BARGAINING_FAIRNESS` | 1 | 1 | 0 | 0 | mean=580943, min=580943, max=580943 | mean=0.580943, min=0.580943, max=0.580943 | 7.990000000000009 | `{"BARGAINING_FAIRNESS":1}` | `{"agent":1}` |
| `bargaining/incomplete-info/finite-horizon/alice/BARGAINING_FAIRNESS` | 1 | 1 | 0 | 0 | mean=5000, min=5000, max=5000 | mean=0.5, min=0.5, max=0.5 | 6.400000000000091 | `{"BARGAINING_FAIRNESS":1}` | `{"agent":1}` |
| `negotiation/complete-info/T1/buyer/NEGOTIATION_FAIRNESS_MARGIN` | 1 | 1 | 0 | 0 | mean=1960, min=1960, max=1960 | mean=0.532667, min=0.532667, max=0.532667 | 3.75 | `{"NEGOTIATION_FAIRNESS_MARGIN":1}` | `{"agent":1}` |
| `negotiation/complete-info/finite-horizon/buyer/NEGOTIATION_FAIRNESS_MARGIN` | 1 | 1 | 0 | 0 | mean=3, min=3, max=3 | mean=0.505, min=0.505, max=0.505 | -4.199999999999932 | `{"NEGOTIATION_FAIRNESS_MARGIN":1}` | `{"hidden":1}` |
| `negotiation/incomplete-info/T1/seller/NEGOTIATION_ADAPTIVE` | 1 | 0 | 1 | 0 | mean=0, min=0, max=0 | mean=0.5, min=0.5, max=0.5 | 1.6399999999999864 | `{"NEGOTIATION_ADAPTIVE":1}` | `{"agent":1}` |
| `negotiation/incomplete-info/finite-horizon/buyer/NEGOTIATION_ADAPTIVE` | 2 | 1 | 1 | 0 | mean=27.62, min=0, max=55.24 | mean=0.546033, min=0.5, max=0.592067 | 2.5 | `{"NEGOTIATION_ADAPTIVE":2}` | `{"agent":2}` |
| `negotiation/incomplete-info/unknown-horizon/buyer/NEGOTIATION_ADAPTIVE` | 1 | 0 | 0 | 1 | mean=0, min=0, max=0 | mean=0.5, min=0.5, max=0.5 | -1.75 | `{"NEGOTIATION_ADAPTIVE":1}` | `{"agent":1}` |
| `persuasion/buyer/repeated/PERSUASION_P0_BABBLING` | 1 | 0 | 0 | 0 | mean=0, min=0, max=0 | n/a | -1.4099999999998545 | `{"PERSUASION_P0_BABBLING":1}` | `{"hidden":1}` |
| `persuasion/seller/repeated/PERSUASION_P0_BABBLING` | 3 | 0 | 0 | 0 | mean=6.66733e+06, min=0, max=2e+07 | n/a | 6.079999999999927 | `{"PERSUASION_P0_BABBLING":3}` | `{"agent":1,"hidden":2}` |

## 13. Exact-cell aggregates

| Exact cell | Role | Selected policy | n | Outcomes | Raw payoff | Scale-adjusted payoff | Rating delta |
| --- | --- | --- | ---: | --- | --- | --- | ---: |
| `bargaining:{"complete_information":false,"delta_1":0.9,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":10000}` | alice | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=5000, min=5000, max=5000 | mean=0.5, min=0.5, max=0.5 | 6.400000000000091 |
| `bargaining:{"complete_information":true,"delta_1":0.8,"delta_2":0.8,"horizon_known":true,"max_rounds":12,"messages_allowed":false,"money_to_divide":10000}` | alice | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=5156.4, min=5156.4, max=5156.4 | mean=0.51564, min=0.51564, max=0.51564 | 2.1399999999998727 |
| `bargaining:{"complete_information":true,"delta_1":0.8,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":false,"money_to_divide":100}` | bob | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=95, min=95, max=95 | mean=0.95, min=0.95, max=0.95 | 6.539999999999964 |
| `bargaining:{"complete_information":true,"delta_1":0.95,"delta_2":0.95,"horizon_known":false,"messages_allowed":true,"money_to_divide":1000000}` | alice | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=580943, min=580943, max=580943 | mean=0.580943, min=0.580943, max=0.580943 | 7.990000000000009 |
| `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_2_role":"buyer","player_2_value":8000.0}` | buyer | `NEGOTIATION_ADAPTIVE` | 1 | `{"walked_away":1}` | mean=0, min=0, max=0 | mean=0.5, min=0.5, max=0.5 | -1.75 |
| `negotiation:{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_1_value":1500000.0,"player_2_role":"buyer"}` | seller | `NEGOTIATION_ADAPTIVE` | 1 | `{"no_deal":1}` | mean=0, min=0, max=0 | mean=0.5, min=0.5, max=0.5 | 1.6399999999999864 |
| `negotiation:{"complete_information":false,"horizon_known":true,"max_rounds":10,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":150.0}` | buyer | `NEGOTIATION_ADAPTIVE` | 1 | `{"agreement":1}` | mean=55.24, min=55.24, max=55.24 | mean=0.592067, min=0.592067, max=0.592067 | 7.230000000000018 |
| `negotiation:{"complete_information":false,"horizon_known":true,"max_rounds":10,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":15000.0}` | buyer | `NEGOTIATION_ADAPTIVE` | 1 | `{"no_deal":1}` | mean=0, min=0, max=0 | mean=0.5, min=0.5, max=0.5 | -4.730000000000018 |
| `negotiation:{"complete_information":true,"horizon_known":true,"max_rounds":1,"messages_allowed":false,"player_1_role":"seller","player_1_value":8000.0,"player_2_role":"buyer","player_2_value":15000.0}` | buyer | `NEGOTIATION_FAIRNESS_MARGIN` | 1 | `{"agreement":1}` | mean=1960, min=1960, max=1960 | mean=0.532667, min=0.532667, max=0.532667 | 3.75 |
| `negotiation:{"complete_information":true,"horizon_known":true,"max_rounds":10,"messages_allowed":true,"player_1_role":"seller","player_1_value":120.0,"player_2_role":"buyer","player_2_value":150.0}` | buyer | `NEGOTIATION_FAIRNESS_MARGIN` | 1 | `{"agreement":1}` | mean=3, min=3, max=3 | mean=0.505, min=0.505, max=0.505 | -4.199999999999932 |
| `persuasion:{"is_seller_know_cv":false,"p":0.3333333333333333,"player_1_role":"seller","player_2_role":"buyer","product_price":10000,"seller_message_type":"binary","total_rounds":20}` | seller | `PERSUASION_P0_BABBLING` | 1 | `{"completed":1}` | mean=0, min=0, max=0 | n/a | -6.329999999999927 |
| `persuasion:{"is_seller_know_cv":false,"p":0.5,"player_1_role":"seller","player_2_role":"buyer","product_price":1000000,"seller_message_type":"binary","total_rounds":20}` | seller | `PERSUASION_P0_BABBLING` | 1 | `{"completed":1}` | mean=2e+07, min=2e+07, max=2e+07 | n/a | 7.059999999999945 |
| `persuasion:{"is_seller_know_cv":true,"p":0.3333333333333333,"player_1_role":"seller","player_2_role":"buyer","product_price":100,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":400.0}` | seller | `PERSUASION_P0_BABBLING` | 1 | `{"completed":1}` | mean=2000, min=2000, max=2000 | n/a | 5.349999999999909 |
| `persuasion:{"is_seller_know_cv":true,"p":0.5,"player_1_role":"seller","player_2_role":"buyer","product_price":100,"seller_message_type":"binary","total_rounds":20,"u":0.0,"v":125.0}` | buyer | `PERSUASION_P0_BABBLING` | 1 | `{"completed":1}` | mean=0, min=0, max=0 | n/a | -1.4099999999998545 |

## 14. Descriptive comparison with the previous pilot

| Policy evidence slice | Descriptive result |
| --- | --- |
| Negotiation static ROBUST (previous) | n=7, agreements=1, no_deals=2, walkaways=4, raw payoff mean=0, min=0, max=0 |
| Negotiation ADAPTIVE (current) | n=4, agreements=1, no_deals=2, walkaways=1, raw payoff mean=13.81, min=0, max=55.24 |
| Complete negotiation extraction theory (previous) | n=2, agreements=1, no_deals=1, walkaways=0, raw payoff mean=100000, min=0, max=200000 |
| Complete negotiation FAIRNESS_MARGIN (current) | n=2, agreements=2, no_deals=0, walkaways=0, raw payoff mean=981.5, min=3, max=1960 |
| Bargaining incumbents (previous) | n=3, agreements=2, no_deals=0, walkaways=1, raw payoff mean=166683, min=0, max=500000 |
| Bargaining FAIRNESS (current) | n=4, agreements=4, no_deals=0, walkaways=0, raw payoff mean=147799, min=95, max=580943 |
| Persuasion seller P0 (previous) | n=1, agreements=0, no_deals=0, walkaways=0, raw payoff mean=0, min=0, max=0 |
| Persuasion seller P3 (current) | n=0, agreements=0, no_deals=0, walkaways=0, raw payoff n/a |

These are nonrandomized matchmaking slices; no causal superiority claim is made.

## 15. Raw rating changes

- negotiation: `974.79 -> 976.73` (delta `1.9400000000000546`).
- bargaining: `1670.46 -> 1693.53` (delta `23.069999999999936`).
- persuasion: `1402.31 -> 1406.98` (delta `4.670000000000073`).

Ratings are reported raw and are not treated as causal estimators.

## 16. Fallbacks, invalid actions, timeouts, and strategic review

Hard stops: `0`; fallbacks: `0`; invalid actions: `0`; timeouts: `0`; strategic-review events: `0`.


## 17. Shutdown state

negotiation: active=0, pending=0; bargaining: active=0, pending=0; persuasion: active=0, pending=0. All family queues were explicitly left.

## 18. Recommendation

Recommend a larger but still bounded randomized-control tranche for `BARGAINING_FAIRNESS` first (4/4 agreements) and `NEGOTIATION_FAIRNESS_MARGIN` second (2/2 agreements). Do not replace their theory controls or call either result causal. `NEGOTIATION_ADAPTIVE` showed one positive-payoff agreement but three zero-payoff outcomes in four games; retain it only for another small diagnostic/randomized bounded block, not broad deployment or replacement of ROBUST. Do not test P3 until its real population trust-rate artifact exists. No larger deployment was started.

## 19. Promotion and execution guard

Every challenger remains `HUMAN_AUTHORIZED_EXPERIMENTAL`, never `E_PROCESS_PROMOTED`. The process-scoped override registry is disabled by default and ended with each pilot process. A larger deployment requires explicit human approval.

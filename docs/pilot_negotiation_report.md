# Negotiation MVL pilot report

Status: **MVL_READY**. Frozen policy commit: `49a6021726553425506a09e23798b813c6091d9a`.

| Requested/completed | Exit | Hard stops | Strategic reviews | Emergency/execution/outer fallbacks | Invalid actions | Policy latency median / p95 / max | Rating before -> after | Shutdown |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| 10/10 | `MAX_GAMES_COMPLETED` | 0 | 0 | 0 | 0 | 0.4145 / 1.2327 / 3.6666 ms | 982.37 -> 974.79 | active=0, pending=0 |

## Games

| # | Game | Configuration | Role / opponent | Incumbent (routing reason) | Actions | Latency median / p95 / max (ms) | Outcome | Raw payoff | Transformed payoff | Rating before -> after |
| ---: | --- | --- | --- | --- | ---: | --- | --- | ---: | --- | --- |
| 1 | `4e6d5310-7f0a-418f-a88e-de3cc4a4dc36` | `{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":1000000.0}` | buyer / hidden:None | `NEGOTIATION_INCOMPLETE_T1_ROBUST` (NO_TRUSTED_PRIOR) | 1 | 0.4973 / 0.4973 / 0.4973 | no_deal | 0 | 0.5 | 982.37 -> 984.03 |
| 2 | `ea9e4deb-5496-4737-a34d-5c47923941eb` | `{"complete_information":true,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_1_value":8000.0,"player_2_role":"buyer","player_2_value":15000.0}` | seller / agent:OpenProgram | `NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT` (direct incumbent) | 1 | 0.3583 / 0.3583 / 0.3583 | agreement | 3500.0 | 0.609375 | 984.03 -> 982.65 |
| 3 | `78e9400f-e035-4b28-9d2b-27bc51a23566` | `{"complete_information":false,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_1_value":120.0,"player_2_role":"buyer"}` | seller / hidden:None | `NEGOTIATION_ROBUST` (BAYES_ELIGIBILITY_UNAVAILABLE) | 13 | 0.3878 / 1.2327 / 1.2327 | walked_away | 0 | 0.5 | 982.65 -> 979.9 |
| 4 | `3933e7fc-4d72-4b80-8dd3-d007a7af5f00` | `{"complete_information":false,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":15000.0}` | buyer / agent:Mew | `NEGOTIATION_ROBUST` (BAYES_ELIGIBILITY_UNAVAILABLE) | 4 | 0.5544 / 1.3802 / 1.3802 | walked_away | 0 | 0.5 | 979.9 -> 975.22 |
| 5 | `bea15bb3-b989-400e-9f11-e51c2cf913cc` | `{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_1_value":1500000.0,"player_2_role":"buyer"}` | seller / agent:pas-2 | `NEGOTIATION_ROBUST` (BAYES_ELIGIBILITY_UNAVAILABLE) | 9 | 0.5168 / 0.8586 / 0.8586 | walked_away | 0 | 0.5 | 975.22 -> 978.79 |
| 6 | `76fae6fe-dee7-4aa6-9eca-5703d019c00a` | `{"complete_information":true,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_1_value":800000.0,"player_2_role":"buyer","player_2_value":1000000.0}` | seller / hidden:None | `NEGOTIATION_COMPLETE_T1_THEORY` (direct incumbent) | 1 | 0.2317 / 0.2317 / 0.2317 | agreement | 200000.0 | 0.5625 | 978.79 -> 986.72 |
| 7 | `69c92a7b-be31-4104-8a29-1d93adcb0447` | `{"complete_information":true,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_1_value":100.0,"player_2_role":"buyer","player_2_value":150.0}` | seller / agent:piglet | `NEGOTIATION_COMPLETE_T1_THEORY` (direct incumbent) | 1 | 0.5650 / 0.5650 / 0.5650 | no_deal | 0 | 0.5 | 986.72 -> 981.95 |
| 8 | `89ad7186-1c36-46d8-ba3b-890922ef47e3` | `{"complete_information":false,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":15000.0}` | buyer / hidden:None | `NEGOTIATION_ROBUST` (BAYES_ELIGIBILITY_UNAVAILABLE) | 12 | 0.5723 / 3.6666 / 3.6666 | walked_away | 0 | 0.5 | 981.95 -> 977.21 |
| 9 | `4822afc6-cc3b-48f5-8fe9-818e45c739a7` | `{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":120.0}` | buyer / agent:Rufus Dufus | `NEGOTIATION_INCOMPLETE_T1_ROBUST` (NO_TRUSTED_PRIOR) | 1 | 0.5840 / 0.5840 / 0.5840 | agreement | 0.0 | 0.5 | 977.21 -> 973.17 |
| 10 | `d5447d28-2b39-4ed4-a0e2-11621567d40b` | `{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":false,"player_1_role":"seller","player_2_role":"buyer","player_2_value":120.0}` | buyer / agent:Bounded Accord | `NEGOTIATION_INCOMPLETE_T1_ROBUST` (NO_TRUSTED_PRIOR) | 1 | 0.3055 / 0.3055 / 0.3055 | no_deal | 0 | 0.5 | 973.17 -> 974.79 |

## Structured action traces

### 1. `4e6d5310-7f0a-418f-a88e-de3cc4a4dc36`

- Actions: `{"decision":"RejectOffer","message":"This is my stated decision."}`
- Route: `NEGOTIATION_INCOMPLETE_T1_ROBUST`; cell `negotiation:{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":1000000.0}`.
- Terminal: `no_deal`; raw payoff `0`.

### 2. `ea9e4deb-5496-4737-a34d-5c47923941eb`

- Actions: `{"message":"I propose the stated price of 11500.0.","product_price":11500.0}`
- Route: `NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT`; cell `negotiation:{"complete_information":true,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_1_value":8000.0,"player_2_role":"buyer","player_2_value":15000.0}`.
- Terminal: `agreement`; raw payoff `3500.0`.

### 3. `78e9400f-e035-4b28-9d2b-27bc51a23566`

- Actions: `{"message":"I propose the stated price of 180.0.","product_price":180.0}`; 12x `{"decision":"RejectOffer","message":"I propose the stated price of 180.0.","product_price":180.0}`
- Route: `NEGOTIATION_ROBUST`; cell `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_1_value":120.0,"player_2_role":"buyer"}`.
- Terminal: `walked_away`; raw payoff `0`.

### 4. `3933e7fc-4d72-4b80-8dd3-d007a7af5f00`

- Actions: 3x `{"decision":"RejectOffer","message":"I propose the stated price of 7500.0.","product_price":7500.0}`; `{"decision":"WalkAway","message":"This is my stated decision."}`
- Route: `NEGOTIATION_ROBUST`; cell `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":15000.0}`.
- Terminal: `walked_away`; raw payoff `0`.

### 5. `bea15bb3-b989-400e-9f11-e51c2cf913cc`

- Actions: `{"product_price":2250000.0}`; 7x `{"decision":"RejectOffer","message":"I propose the stated price of 2250000.0.","product_price":2250000.0}`; `{"decision":"WalkAway","message":"This is my stated decision."}`
- Route: `NEGOTIATION_ROBUST`; cell `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_1_value":1500000.0,"player_2_role":"buyer"}`.
- Terminal: `walked_away`; raw payoff `0`.

### 6. `76fae6fe-dee7-4aa6-9eca-5703d019c00a`

- Actions: `{"message":"I propose the stated price of 1000000.0.","product_price":1000000.0}`
- Route: `NEGOTIATION_COMPLETE_T1_THEORY`; cell `negotiation:{"complete_information":true,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_1_value":800000.0,"player_2_role":"buyer","player_2_value":1000000.0}`.
- Terminal: `agreement`; raw payoff `200000.0`.

### 7. `69c92a7b-be31-4104-8a29-1d93adcb0447`

- Actions: `{"message":"I propose the stated price of 150.0.","product_price":150.0}`
- Route: `NEGOTIATION_COMPLETE_T1_THEORY`; cell `negotiation:{"complete_information":true,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_1_value":100.0,"player_2_role":"buyer","player_2_value":150.0}`.
- Terminal: `no_deal`; raw payoff `0`.

### 8. `89ad7186-1c36-46d8-ba3b-890922ef47e3`

- Actions: 12x `{"decision":"RejectOffer","message":"I propose the stated price of 7500.0.","product_price":7500.0}`
- Route: `NEGOTIATION_ROBUST`; cell `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":15000.0}`.
- Terminal: `walked_away`; raw payoff `0`.

### 9. `4822afc6-cc3b-48f5-8fe9-818e45c739a7`

- Actions: `{"decision":"AcceptOffer","message":"This is my stated decision."}`
- Route: `NEGOTIATION_INCOMPLETE_T1_ROBUST`; cell `negotiation:{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":120.0}`.
- Terminal: `agreement`; raw payoff `0.0`.

### 10. `d5447d28-2b39-4ed4-a0e2-11621567d40b`

- Actions: `{"decision":"RejectOffer","message":"This is my stated decision."}`
- Route: `NEGOTIATION_INCOMPLETE_T1_ROBUST`; cell `negotiation:{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":false,"player_1_role":"seller","player_2_role":"buyer","player_2_value":120.0}`.
- Terminal: `no_deal`; raw payoff `0`.

## Per-cell / role results

| Cell | Role | n | Outcomes | Payoffs | No-deal/walk-away floor | Strategic status |
| --- | --- | ---: | --- | --- | ---: | --- |
| `negotiation:{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":1000000.0}` | buyer | 1 | {"no_deal":1} | [0] | 1/1 | monitor: below n=3 threshold |
| `negotiation:{"complete_information":true,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_1_value":8000.0,"player_2_role":"buyer","player_2_value":15000.0}` | seller | 1 | {"agreement":1} | [3500.0] | 0/1 | clear |
| `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_1_value":120.0,"player_2_role":"buyer"}` | seller | 1 | {"walked_away":1} | [0] | 1/1 | monitor: below n=3 threshold |
| `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":15000.0}` | buyer | 2 | {"walked_away":2} | [0,0] | 2/2 | monitor: below n=3 threshold |
| `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_1_value":1500000.0,"player_2_role":"buyer"}` | seller | 1 | {"walked_away":1} | [0] | 1/1 | monitor: below n=3 threshold |
| `negotiation:{"complete_information":true,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_1_value":800000.0,"player_2_role":"buyer","player_2_value":1000000.0}` | seller | 1 | {"agreement":1} | [200000.0] | 0/1 | clear |
| `negotiation:{"complete_information":true,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_1_value":100.0,"player_2_role":"buyer","player_2_value":150.0}` | seller | 1 | {"no_deal":1} | [0] | 1/1 | monitor: below n=3 threshold |
| `negotiation:{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":true,"player_1_role":"seller","player_2_role":"buyer","player_2_value":120.0}` | buyer | 1 | {"agreement":1} | [0.0] | 0/1 | clear |
| `negotiation:{"complete_information":false,"horizon_known":true,"max_rounds":1,"messages_allowed":false,"player_1_role":"seller","player_2_role":"buyer","player_2_value":120.0}` | buyer | 1 | {"no_deal":1} | [0] | 1/1 | monitor: below n=3 threshold |

The JSONL transcript is authoritative for every received state, routing derivation, submitted action, terminal payload, and rating poll. Rating improvement was not a pass condition.

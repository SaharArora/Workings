# Persuasion MVL pilot report

Status: **MVL_READY**. Frozen policy commit: `49a6021726553425506a09e23798b813c6091d9a`.

| Requested/completed | Exit | Hard stops | Strategic reviews | Emergency/execution/outer fallbacks | Invalid actions | Policy latency median / p95 / max | Rating before -> after | Shutdown |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| 3/3 | `MAX_GAMES_COMPLETED` | 0 | 0 | 0 | 0 | 0.2018 / 0.5192 / 3.4058 ms | 1403.77 -> 1402.31 | active=0, pending=0 |

## Games

| # | Game | Configuration | Role / opponent | Incumbent (routing reason) | Actions | Latency median / p95 / max (ms) | Outcome | Raw payoff | Transformed payoff | Rating before -> after |
| ---: | --- | --- | --- | --- | ---: | --- | --- | ---: | --- | --- |
| 1 | `fecece80-50eb-4ad3-885d-ac6c1fbdb812` | `{"is_seller_know_cv":false,"p":0.8,"product_price":1000000,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":1200000.0}` | buyer / agent:test4 | `PERSUASION_P0_BABBLING` (direct incumbent) | 20 | 0.2159 / 0.5192 / 0.5807 | completed | 0.0 | n/a | 1403.77 -> 1405.03 |
| 2 | `35d004a1-862b-4850-974e-4fffccc2502a` | `{"is_seller_know_cv":true,"p":0.3333333333333333,"product_price":1000000,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":2000000.0}` | seller / hidden:None | `PERSUASION_P0_BABBLING` (direct incumbent) | 20 | 0.1591 / 0.3734 / 1.9300 | completed | 0.0 | n/a | 1405.03 -> 1399.92 |
| 3 | `f21ecf19-179e-4faa-940f-dbc8324b8476` | `{"is_seller_know_cv":false,"p":0.3333333333333333,"product_price":1000000,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":4000000.0}` | buyer / agent:eta | `PERSUASION_P0_BABBLING` (direct incumbent) | 20 | 0.2601 / 0.3754 / 3.4058 | completed | 8000000.0 | n/a | 1399.92 -> 1402.31 |

## Structured action traces

### 1. `fecece80-50eb-4ad3-885d-ac6c1fbdb812`

- Actions: 20x `{"decision":"no"}`
- Route: `PERSUASION_P0_BABBLING`; cell `persuasion:{"is_seller_know_cv":false,"p":0.8,"player_1_role":"seller","player_2_role":"buyer","product_price":1000000,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":1200000.0}`.
- Terminal: `completed`; raw payoff `0.0`.

### 2. `35d004a1-862b-4850-974e-4fffccc2502a`

- Actions: 20x `{"message":"This is my stated decision."}`
- Route: `PERSUASION_P0_BABBLING`; cell `persuasion:{"is_seller_know_cv":true,"p":0.3333333333333333,"player_1_role":"seller","player_2_role":"buyer","product_price":1000000,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":2000000.0}`.
- Terminal: `completed`; raw payoff `0.0`.

### 3. `f21ecf19-179e-4faa-940f-dbc8324b8476`

- Actions: 20x `{"decision":"yes"}`
- Route: `PERSUASION_P0_BABBLING`; cell `persuasion:{"is_seller_know_cv":false,"p":0.3333333333333333,"player_1_role":"seller","player_2_role":"buyer","product_price":1000000,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":4000000.0}`.
- Terminal: `completed`; raw payoff `8000000.0`.

## Per-cell / role results

| Cell | Role | n | Outcomes | Payoffs | No-deal/walk-away floor | Strategic status |
| --- | --- | ---: | --- | --- | ---: | --- |
| `persuasion:{"is_seller_know_cv":false,"p":0.8,"player_1_role":"seller","player_2_role":"buyer","product_price":1000000,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":1200000.0}` | buyer | 1 | {"completed":1} | [0.0] | 0/1 | clear |
| `persuasion:{"is_seller_know_cv":true,"p":0.3333333333333333,"player_1_role":"seller","player_2_role":"buyer","product_price":1000000,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":2000000.0}` | seller | 1 | {"completed":1} | [0.0] | 0/1 | clear |
| `persuasion:{"is_seller_know_cv":false,"p":0.3333333333333333,"player_1_role":"seller","player_2_role":"buyer","product_price":1000000,"seller_message_type":"text","total_rounds":20,"u":0.0,"v":4000000.0}` | buyer | 1 | {"completed":1} | [8000000.0] | 0/1 | clear |

The JSONL transcript is authoritative for every received state, routing derivation, submitted action, terminal payload, and rating poll. Rating improvement was not a pass condition.

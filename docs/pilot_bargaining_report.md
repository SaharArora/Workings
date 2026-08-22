# Bargaining MVL pilot report

Status: **MVL_READY**. Frozen policy commit: `49a6021726553425506a09e23798b813c6091d9a`.

| Requested/completed | Exit | Hard stops | Strategic reviews | Emergency/execution/outer fallbacks | Invalid actions | Policy latency median / p95 / max | Rating before -> after | Shutdown |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| 3/3 | `MAX_GAMES_COMPLETED` | 0 | 0 | 0 | 0 | 0.3727 / 2.1858 / 2.1858 ms | 1680.69 -> 1670.46 | active=0, pending=0 |

## Games

| # | Game | Configuration | Role / opponent | Incumbent (routing reason) | Actions | Latency median / p95 / max (ms) | Outcome | Raw payoff | Transformed payoff | Rating before -> after |
| ---: | --- | --- | --- | --- | ---: | --- | --- | ---: | --- | --- |
| 1 | `9c3486e9-176c-4b8f-abdb-eaed63cb83bf` | `{"complete_information":false,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":1000000}` | bob / agent:Wooper | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` (OPPONENT_DELTA_PRIOR_UNAVAILABLE) | 2 | 0.3884 / 0.6440 / 0.6440 | agreement | 500000.0 | n/a | 1680.69 -> 1679.45 |
| 2 | `b99297e7-93da-4b25-9441-a2fd88bc185f` | `{"complete_information":true,"delta_1":0.9,"delta_2":1.0,"horizon_known":false,"messages_allowed":false,"money_to_divide":10000}` | bob / agent:Ira | `BARGAINING_COMPLETE_UNLIMITED` (direct incumbent) | 5 | 0.3727 / 2.1858 / 2.1858 | walked_away | 0 | n/a | 1679.45 -> 1672.78 |
| 3 | `17bc6044-c40d-4e0b-a4d5-aedf0b8f2e78` | `{"complete_information":false,"delta_2":1.0,"horizon_known":false,"messages_allowed":false,"money_to_divide":100}` | bob / agent:A1 | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` (OPPONENT_DELTA_PRIOR_UNAVAILABLE) | 2 | 0.7203 / 1.2395 / 1.2395 | agreement | 50.0 | n/a | 1672.78 -> 1670.46 |

## Structured action traces

### 1. `9c3486e9-176c-4b8f-abdb-eaed63cb83bf`

- Actions: `{"decision":"reject"}`; `{"alice_gain":500000.0,"bob_gain":500000.0,"message":"I propose the stated allocation."}`
- Route: `BARGAINING_INCOMPLETE_EQUAL_SPLIT`; cell `bargaining:{"complete_information":false,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":1000000}`.
- Terminal: `agreement`; raw payoff `500000.0`.

### 2. `b99297e7-93da-4b25-9441-a2fd88bc185f`

- Actions: `{"decision":"reject"}`; `{"alice_gain":0.0,"bob_gain":10000.0}`; `{"decision":"reject"}`; `{"alice_gain":0.0,"bob_gain":10000.0}`; `{"decision":"walkaway"}`
- Route: `BARGAINING_COMPLETE_UNLIMITED`; cell `bargaining:{"complete_information":true,"delta_1":0.9,"delta_2":1.0,"horizon_known":false,"messages_allowed":false,"money_to_divide":10000}`.
- Terminal: `walked_away`; raw payoff `0`.

### 3. `17bc6044-c40d-4e0b-a4d5-aedf0b8f2e78`

- Actions: `{"decision":"reject"}`; `{"alice_gain":50.0,"bob_gain":50.0}`
- Route: `BARGAINING_INCOMPLETE_EQUAL_SPLIT`; cell `bargaining:{"complete_information":false,"delta_2":1.0,"horizon_known":false,"messages_allowed":false,"money_to_divide":100}`.
- Terminal: `agreement`; raw payoff `50.0`.

## Per-cell / role results

| Cell | Role | n | Outcomes | Payoffs | No-deal/walk-away floor | Strategic status |
| --- | --- | ---: | --- | --- | ---: | --- |
| `bargaining:{"complete_information":false,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":1000000}` | bob | 1 | {"agreement":1} | [500000.0] | 0/1 | clear |
| `bargaining:{"complete_information":true,"delta_1":0.9,"delta_2":1.0,"horizon_known":false,"messages_allowed":false,"money_to_divide":10000}` | bob | 1 | {"walked_away":1} | [0] | 1/1 | monitor: below n=3 threshold |
| `bargaining:{"complete_information":false,"delta_2":1.0,"horizon_known":false,"messages_allowed":false,"money_to_divide":100}` | bob | 1 | {"agreement":1} | [50.0] | 0/1 | clear |

The JSONL transcript is authoritative for every received state, routing derivation, submitted action, terminal payload, and rating poll. Rating improvement was not a pass condition.

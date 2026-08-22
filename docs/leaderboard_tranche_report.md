# Time-constrained leaderboard tranche report

## 1. Commits and tests

- Frozen tranche commit: `9fcae232ea1f6f474ad5382c0936bd1f1a0a5b4d`.
- Final report commit: recorded in the completion response after this generated report is committed.
- Tests: `234 passed before live execution; 234 passed after shutdown`.

No policy or threshold changed after the first tranche game.

Requested/completed: bargaining 20/20; negotiation 6/20 before a stopped incumbent
class made further matchmaking unsafe; persuasion 5/12 before its sole seller incumbent
class paused. Controlled queue calls, tracked IDs, and completed IDs were respectively
20/20/20, 6/6/6, and 5/5/5. No uncontrolled extra game was created.

The transcripts contain 31 unique terminal games and 229 submitted structured actions.
There were zero invalid results, strategy or policy-execution fallbacks, unsupported
routes, hard operational stops, timeouts, extra games, P3 selections, or e-process
promotion labels. Maximum local policy latency was 0.004592 seconds, safely below the
30-second ceiling.

## 2. Acceptance-rule audit

`STATIC_ROBUST_OLD_ACCEPTANCE_RULE_ACTIVE = yes`

`ADAPTIVE_OLD_ACCEPTANCE_RULE_ACTIVE = no`

Static ROBUST retains its implementation-added fixed-proposal acceptance threshold. ADAPTIVE uses terminal IR acceptance and its 0.90 adaptive continuation-target threshold; the two behaviors have a direct regression test.

## 3. Frozen production policy map

The exact map and predeclared stop rules are in `docs/leaderboard_tranche_plan.md`. In brief: bargaining FAIRNESS where defined; complete finite negotiation FAIRNESS_MARGIN while exact theory remains control; II/T=1 one-shot incumbent; incomplete multi-round/unknown incumbent hierarchy with at most six nonrandom ADAPTIVE diagnostics; persuasion P0. Manual challenger use remains `HUMAN_AUTHORIZED_EXPERIMENTAL` or `HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC`, never `E_PROCESS_PROMOTED`.

## 4. Bargaining game-by-game

| # | Game | Configuration | Role / opponent | Control | Authorization | Selected | Structured actions | Outcome | Raw payoff | Normalized/transformed | Rating |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | `e63c215a-586b-492c-847b-6818c0025efb` | `{"complete_information":true,"delta_1":1.0,"delta_2":1.0,"horizon_known":false,"messages_allowed":false,"money_to_divide":1000000}` | bob / hidden:None | `BARGAINING_COMPLETE_UNLIMITED` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"decision":"accept"}` | agreement | 500000.0 | 0.5 | 1693.53 -> 1693.52 |
| 2 | `b6778a45-27bb-40b7-b23d-1287f2485499` | `{"complete_information":false,"delta_2":0.9,"horizon_known":false,"messages_allowed":true,"money_to_divide":1000000}` | bob / hidden:None | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"decision":"reject"}`; `{"alice_gain":500000.0,"bob_gain":500000.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":500000.0,"bob_gain":500000.0,"message":"I propose the stated allocation."}`; `{"decision":"walkaway"}` | walked_away | 0 | 0.0 | 1693.52 -> 1686.78 |
| 3 | `ad125cc6-1ddc-4466-8564-2b1f6c6f00f6` | `{"complete_information":true,"delta_1":1.0,"delta_2":0.8,"horizon_known":false,"messages_allowed":true,"money_to_divide":100}` | bob / hidden:None | `BARGAINING_COMPLETE_UNLIMITED` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"decision":"accept"}` | agreement | 40.0 | 0.4 | 1686.78 -> 1691.05 |
| 4 | `551dc7a8-f535-4fad-9e34-15ca91611534` | `{"complete_information":true,"delta_1":0.95,"delta_2":0.8,"horizon_known":true,"max_rounds":12,"messages_allowed":false,"money_to_divide":1000000}` | alice / agent:BizarreBazar | `BARGAINING_COMPLETE_FINITE` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"alice_gain":655475.053568,"bob_gain":344524.946432}` | agreement | 655475.05 | 0.6554750500000001 | 1691.05 -> 1697.32 |
| 5 | `a2fcb808-f675-41e4-b91c-5c130aacabe7` | `{"complete_information":false,"delta_1":0.95,"horizon_known":false,"messages_allowed":false,"money_to_divide":1000000}` | alice / hidden:None | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"alice_gain":500000.0,"bob_gain":500000.0}`; `{"decision":"reject"}`; `{"alice_gain":500000.0,"bob_gain":500000.0}`; `{"decision":"reject"}`; `{"alice_gain":500000.0,"bob_gain":500000.0}`; `{"decision":"walkaway"}` | walked_away | 0 | 0.0 | 1697.32 -> 1690.82 |
| 6 | `d48f1d82-5084-4247-a5fc-99d4b598ca06` | `{"complete_information":false,"delta_1":0.8,"horizon_known":false,"messages_allowed":true,"money_to_divide":100}` | alice / hidden:None | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"alice_gain":50.0,"bob_gain":50.0,"message":"I propose the stated allocation."}` | agreement | 50.0 | 0.5 | 1690.82 -> 1690.47 |
| 7 | `365ab777-3387-4f0c-9980-0a8d947dfd3d` | `{"complete_information":true,"delta_1":1.0,"delta_2":0.95,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":1000000}` | bob / agent:7aidara_Alpha | `BARGAINING_COMPLETE_FINITE` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"decision":"reject"}`; `{"alice_gain":253597.15625000012,"bob_gain":746402.8437499999,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":216944.3750000001,"bob_gain":783055.6249999999,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":178362.5000000001,"bob_gain":821637.4999999999,"message":"I propose the stated allocation."}` | agreement | 635767.44 | 0.63576744 | 1690.47 -> 1696.82 |
| 8 | `def0fb60-3e2d-4aad-8041-c48338f06ff2` | `{"complete_information":false,"delta_2":1.0,"horizon_known":false,"messages_allowed":true,"money_to_divide":10000}` | bob / hidden:None | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `PORTFOLIO_INCUMBENT` | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `{"decision":"reject"}`; `{"alice_gain":5000.0,"bob_gain":5000.0,"message":"I propose the stated allocation."}` | agreement | 5000.0 | 0.5 | 1696.82 -> 1697.92 |
| 9 | `c377cc3e-9834-4f45-aa3c-a6f1a844137b` | `{"complete_information":false,"delta_2":0.8,"horizon_known":false,"messages_allowed":true,"money_to_divide":10000}` | bob / agent:7aidara_Beta | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `PORTFOLIO_INCUMBENT` | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `{"decision":"accept"}` | agreement | 5000.0 | 0.5 | 1697.92 -> 1704.69 |
| 10 | `c76dd4d0-eaee-4fa3-9e8c-503fc9e8e6e0` | `{"complete_information":false,"delta_1":0.95,"horizon_known":false,"messages_allowed":true,"money_to_divide":1000000}` | alice / hidden:None | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `PORTFOLIO_INCUMBENT` | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `{"alice_gain":500000.0,"bob_gain":500000.0,"message":"I propose the stated allocation."}` | agreement | 500000.0 | 0.5 | 1704.69 -> 1704.98 |
| 11 | `ffb66ca3-353c-4ee1-8d4c-671dafab28e9` | `{"complete_information":true,"delta_1":0.95,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":false,"money_to_divide":1000000}` | alice / agent:velocity | `BARGAINING_COMPLETE_FINITE` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"alice_gain":50000.0,"bob_gain":950000.0}` | agreement | 50000.0 | 0.05 | 1704.98 -> 1699.54 |
| 12 | `17de308f-84ff-41a4-8d77-4e6886d38120` | `{"complete_information":true,"delta_1":0.95,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":false,"money_to_divide":1000000}` | bob / hidden:None | `BARGAINING_COMPLETE_FINITE` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"decision":"reject"}`; `{"alice_gain":50000.000000000044,"bob_gain":950000.0}`; `{"decision":"reject"}`; `{"alice_gain":50000.000000000044,"bob_gain":950000.0}`; `{"decision":"reject"}`; `{"alice_gain":50000.000000000044,"bob_gain":950000.0}`; `{"decision":"reject"}`; `{"alice_gain":50000.000000000044,"bob_gain":950000.0}` | agreement | 950000.0 | 0.95 | 1699.54 -> 1705.06 |
| 13 | `301b93a0-8fdd-494e-b0e9-bb7101379e82` | `{"complete_information":false,"delta_1":0.8,"horizon_known":false,"messages_allowed":false,"money_to_divide":100}` | alice / agent:Rufus Dufus | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `PORTFOLIO_INCUMBENT` | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `{"alice_gain":50.0,"bob_gain":50.0}` | agreement | 50.0 | 0.5 | 1705.06 -> 1709.58 |
| 14 | `cf556db6-7f17-4d5b-a7dd-b8feb0480c5b` | `{"complete_information":true,"delta_1":1.0,"delta_2":0.95,"horizon_known":false,"messages_allowed":false,"money_to_divide":1000000}` | alice / hidden:None | `BARGAINING_COMPLETE_UNLIMITED` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"alice_gain":950000.0,"bob_gain":50000.000000000044}` | agreement | 950000.0 | 0.95 | 1709.58 -> 1717.68 |
| 15 | `c0f321cc-a40f-4812-9d2d-4e7e1f9c8d98` | `{"complete_information":false,"delta_1":1.0,"horizon_known":false,"messages_allowed":true,"money_to_divide":100}` | alice / hidden:None | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `PORTFOLIO_INCUMBENT` | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `{"alice_gain":50.0,"bob_gain":50.0,"message":"I propose the stated allocation."}` | agreement | 50.0 | 0.5 | 1717.68 -> 1718.74 |
| 16 | `d6a702f5-c112-4d92-bab5-de61329dccd2` | `{"complete_information":false,"delta_1":0.9,"horizon_known":false,"messages_allowed":false,"money_to_divide":10000}` | alice / agent:test4 | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `PORTFOLIO_INCUMBENT` | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `{"alice_gain":5000.0,"bob_gain":5000.0}` | agreement | 5000.0 | 0.5 | 1718.74 -> 1716.99 |
| 17 | `73259826-4e29-4956-a4c3-471bbd83e622` | `{"complete_information":true,"delta_1":1.0,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":10000}` | bob / hidden:None | `BARGAINING_COMPLETE_FINITE` | `HUMAN_AUTHORIZED_EXPERIMENTAL` | `BARGAINING_FAIRNESS` | `{"decision":"reject"}`; `{"alice_gain":500.00000000000045,"bob_gain":9500.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":500.00000000000045,"bob_gain":9500.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":500.00000000000045,"bob_gain":9500.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":500.00000000000045,"bob_gain":9500.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":500.00000000000045,"bob_gain":9500.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":500.00000000000045,"bob_gain":9500.0,"message":"I propose the stated allocation."}` | agreement | 9500.0 | 0.95 | 1716.99 -> 1724.76 |
| 18 | `4c9e8317-e75b-457d-818d-0017859823a9` | `{"complete_information":false,"delta_2":0.95,"horizon_known":false,"messages_allowed":true,"money_to_divide":10000}` | bob / agent:Athena | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `PORTFOLIO_INCUMBENT` | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `{"decision":"reject"}`; `{"alice_gain":5000.0,"bob_gain":5000.0,"message":"I propose the stated allocation."}` | agreement | 4750.0 | 0.475 | 1724.76 -> 1726.33 |
| 19 | `338e2f0d-4430-4c02-8ce0-fbd1ec6b9a98` | `{"complete_information":false,"delta_2":0.95,"horizon_known":false,"messages_allowed":true,"money_to_divide":10000}` | bob / agent:theta | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `PORTFOLIO_INCUMBENT` | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | `{"decision":"reject"}`; `{"alice_gain":5000.0,"bob_gain":5000.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":5000.0,"bob_gain":5000.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":5000.0,"bob_gain":5000.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":5000.0,"bob_gain":5000.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":5000.0,"bob_gain":5000.0,"message":"I propose the stated allocation."}`; `{"decision":"walkaway"}` | walked_away | 0 | 0.0 | 1726.33 -> 1719.39 |
| 20 | `a2cd8420-195c-45e5-81a3-f29cd2ee7d22` | `{"complete_information":true,"delta_1":0.9,"delta_2":0.95,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":10000}` | bob / agent:Harvey Specter | `BARGAINING_COMPLETE_FINITE` | `THEORY_INCUMBENT` | `BARGAINING_COMPLETE_FINITE` | `{"decision":"reject"}`; `{"alice_gain":1685.4520165312515,"bob_gain":8314.547983468748,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":1444.9731187500015,"bob_gain":8555.026881249998,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":1163.7112500000012,"bob_gain":8836.288749999998,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":834.7500000000008,"bob_gain":9165.25,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":450.0000000000004,"bob_gain":9550.0,"message":"I propose the stated allocation."}`; `{"decision":"reject"}`; `{"alice_gain":0.0,"bob_gain":10000.0,"message":"I propose the stated allocation."}` | no_deal | 0 | 0.0 | 1719.39 -> 1712.58 |

## 5. Negotiation game-by-game

| # | Game | Configuration | Role / opponent | Control | Authorization | Selected | Structured actions | Outcome | Raw payoff | Normalized/transformed | Rating |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | `45cdbd4a-2b42-41c4-a58f-7d17c79e4563` | `{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_1_value":150.0,"player_2_role":"buyer"}` | seller / agent:Harsanyi | `NEGOTIATION_ROBUST` | `HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC` | `NEGOTIATION_ADAPTIVE` | `{"product_price":225.0}`; 12x `{"decision":"RejectOffer","message":"I propose the stated price of 225.0.","product_price":225.0}`; `{"decision":"WalkAway","message":"This is my stated decision."}` | walked_away | 0 | 0.5 | 976.73 -> 974.44 |
| 2 | `db1b5062-b60c-4a5e-867a-eb08c155f758` | `{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_1_value":120.0,"player_2_role":"buyer"}` | seller / hidden:None | `NEGOTIATION_ROBUST` | `PORTFOLIO_INCUMBENT` | `NEGOTIATION_ROBUST` | `{"product_price":180.0}`; 12x `{"decision":"RejectOffer","message":"I propose the stated price of 180.0.","product_price":180.0}` | walked_away | 0 | 0.5 | 974.44 -> 969.57 |
| 3 | `344cd97e-6dff-4cfe-ab0f-e41f452b9f6b` | `{"complete_information":false,"horizon_known":true,"max_rounds":10,"messages_allowed":false,"player_1_role":"seller","player_2_role":"buyer","player_2_value":1000000.0}` | buyer / agent:champion | `NEGOTIATION_ROBUST` | `HUMAN_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC` | `NEGOTIATION_ADAPTIVE` | 5x `{"decision":"RejectOffer","message":"I propose the stated price of 500000.0.","product_price":500000.0}` | no_deal | 0 | 0.5 | 969.57 -> 968.04 |
| 4 | `291238c8-0190-4e50-84a6-d778e0e22717` | `{"complete_information":true,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_1_value":120.0,"player_2_role":"buyer","player_2_value":150.0}` | buyer / agent:p00h | `NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT` | `THEORY_INCUMBENT` | `NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT` | `{"decision":"AcceptOffer","message":"This is my stated decision."}` | agreement | 15.0 | 0.525 | 968.04 -> 968.06 |
| 5 | `3d41265c-6ab7-47fa-8cce-cd59681f5e35` | `{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_2_role":"buyer","player_2_value":10000.0}` | buyer / hidden:None | `NEGOTIATION_ROBUST` | `PORTFOLIO_INCUMBENT` | `NEGOTIATION_ROBUST` | 12x `{"decision":"RejectOffer","message":"I propose the stated price of 5000.0.","product_price":5000.0}` | walked_away | 0 | 0.5 | 968.06 -> 966.45 |
| 6 | `604228d0-dba7-44eb-b7fb-a3bcb9b5f71d` | `{"complete_information":false,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_1_value":15000.0,"player_2_role":"buyer"}` | seller / agent:AgentC | `NEGOTIATION_ROBUST` | `PORTFOLIO_INCUMBENT` | `NEGOTIATION_ROBUST` | `{"message":"I propose the stated price of 22500.0.","product_price":22500.0}`; 7x `{"decision":"RejectOffer","message":"I propose the stated price of 22500.0.","product_price":22500.0}`; `{"decision":"WalkAway","message":"This is my stated decision."}` | walked_away | 0 | 0.5 | 966.45 -> 969.14 |

## 6. Persuasion game-by-game

| # | Game | Configuration | Role / opponent | Control | Authorization | Selected | Structured actions | Outcome | Raw payoff | Normalized/transformed | Rating |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | `4b37892d-793d-4a66-a610-5f09bc059423` | `{"is_seller_know_cv":false,"p":0.8,"product_price":10000,"seller_message_type":"binary","total_rounds":20}` | seller / hidden:None | `PERSUASION_P0_BABBLING` | `THEORY_INCUMBENT` | `PERSUASION_P0_BABBLING` | 20x `{"decision":"yes"}` | completed | 0.0 | None | 1406.98 -> 1401.36 |
| 2 | `c64c813e-a4d3-4355-a635-71c9d1ccf76f` | `{"is_seller_know_cv":false,"p":0.8,"product_price":1000000,"seller_message_type":"binary","total_rounds":20,"u":0.0,"v":1250000.0}` | buyer / agent:NegoMind-B | `PERSUASION_P0_BABBLING` | `THEORY_INCUMBENT` | `PERSUASION_P0_BABBLING` | 20x `{"decision":"yes"}` | completed | -1250000.0 | None | 1401.36 -> 1395.29 |
| 3 | `d4ca18b5-8228-4f09-94a5-be8d20ab29bf` | `{"is_seller_know_cv":false,"p":0.3333333333333333,"product_price":100,"seller_message_type":"binary","total_rounds":20}` | seller / hidden:None | `PERSUASION_P0_BABBLING` | `THEORY_INCUMBENT` | `PERSUASION_P0_BABBLING` | 20x `{"decision":"yes"}` | completed | 200.0 | None | 1395.29 -> 1389.57 |
| 4 | `70304cc7-30bb-481b-b3d5-da7bb43ff774` | `{"is_seller_know_cv":true,"p":0.3333333333333333,"product_price":100,"seller_message_type":"binary","total_rounds":20,"u":0.0,"v":200.0}` | buyer / agent:Harvey Specter | `PERSUASION_P0_BABBLING` | `THEORY_INCUMBENT` | `PERSUASION_P0_BABBLING` | 20x `{"decision":"no"}` | completed | 0.0 | None | 1389.57 -> 1387.45 |
| 5 | `b1d99bd7-0661-4d18-8232-fe6841c75f11` | `{"is_seller_know_cv":true,"p":0.8,"product_price":10000,"seller_message_type":"binary","total_rounds":20,"u":0.0,"v":12000.0}` | seller / agent:NegoMind-B | `PERSUASION_P0_BABBLING` | `THEORY_INCUMBENT` | `PERSUASION_P0_BABBLING` | 20x `{"decision":"yes"}` | completed | 0.0 | None | 1387.45 -> 1383.34 |

## 7. Exact-cell aggregates

| Exact cell | Role | Policy | n | Outcomes | Raw payoff | Normalized/transformed | Rating delta |
| --- | --- | --- | ---: | --- | --- | --- | ---: |
| `bargaining:{"complete_information":false,"delta_1":0.8,"horizon_known":false,"messages_allowed":false,"money_to_divide":100}` | alice | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 1 | `{"agreement":1}` | mean=50; median=50 | mean=0.5; median=0.5 | 4.519999999999982 |
| `bargaining:{"complete_information":false,"delta_1":0.8,"horizon_known":false,"messages_allowed":true,"money_to_divide":100}` | alice | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=50; median=50 | mean=0.5; median=0.5 | -0.34999999999990905 |
| `bargaining:{"complete_information":false,"delta_1":0.9,"horizon_known":false,"messages_allowed":false,"money_to_divide":10000}` | alice | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 1 | `{"agreement":1}` | mean=5000; median=5000 | mean=0.5; median=0.5 | -1.75 |
| `bargaining:{"complete_information":false,"delta_1":0.95,"horizon_known":false,"messages_allowed":false,"money_to_divide":1000000}` | alice | `BARGAINING_FAIRNESS` | 1 | `{"walked_away":1}` | mean=0; median=0 | mean=0; median=0 | -6.5 |
| `bargaining:{"complete_information":false,"delta_1":0.95,"horizon_known":false,"messages_allowed":true,"money_to_divide":1000000}` | alice | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 1 | `{"agreement":1}` | mean=500000; median=500000 | mean=0.5; median=0.5 | 0.2899999999999636 |
| `bargaining:{"complete_information":false,"delta_1":1.0,"horizon_known":false,"messages_allowed":true,"money_to_divide":100}` | alice | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 1 | `{"agreement":1}` | mean=50; median=50 | mean=0.5; median=0.5 | 1.0599999999999454 |
| `bargaining:{"complete_information":false,"delta_2":0.8,"horizon_known":false,"messages_allowed":true,"money_to_divide":10000}` | bob | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 1 | `{"agreement":1}` | mean=5000; median=5000 | mean=0.5; median=0.5 | 6.769999999999982 |
| `bargaining:{"complete_information":false,"delta_2":0.9,"horizon_known":false,"messages_allowed":true,"money_to_divide":1000000}` | bob | `BARGAINING_FAIRNESS` | 1 | `{"walked_away":1}` | mean=0; median=0 | mean=0; median=0 | -6.740000000000009 |
| `bargaining:{"complete_information":false,"delta_2":0.95,"horizon_known":false,"messages_allowed":true,"money_to_divide":10000}` | bob | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 2 | `{"agreement":1,"walked_away":1}` | mean=2375; median=2375 | mean=0.2375; median=0.2375 | -5.369999999999891 |
| `bargaining:{"complete_information":false,"delta_2":1.0,"horizon_known":false,"messages_allowed":true,"money_to_divide":10000}` | bob | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 1 | `{"agreement":1}` | mean=5000; median=5000 | mean=0.5; median=0.5 | 1.1000000000001364 |
| `bargaining:{"complete_information":true,"delta_1":0.9,"delta_2":0.95,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":10000}` | bob | `BARGAINING_COMPLETE_FINITE` | 1 | `{"no_deal":1}` | mean=0; median=0 | mean=0; median=0 | -6.810000000000173 |
| `bargaining:{"complete_information":true,"delta_1":0.95,"delta_2":0.8,"horizon_known":true,"max_rounds":12,"messages_allowed":false,"money_to_divide":1000000}` | alice | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=655475; median=655475 | mean=0.655475; median=0.655475 | 6.269999999999982 |
| `bargaining:{"complete_information":true,"delta_1":0.95,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":false,"money_to_divide":1000000}` | alice | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=50000; median=50000 | mean=0.05; median=0.05 | -5.440000000000055 |
| `bargaining:{"complete_information":true,"delta_1":0.95,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":false,"money_to_divide":1000000}` | bob | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=950000; median=950000 | mean=0.95; median=0.95 | 5.519999999999982 |
| `bargaining:{"complete_information":true,"delta_1":1.0,"delta_2":0.8,"horizon_known":false,"messages_allowed":true,"money_to_divide":100}` | bob | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=40; median=40 | mean=0.4; median=0.4 | 4.269999999999982 |
| `bargaining:{"complete_information":true,"delta_1":1.0,"delta_2":0.95,"horizon_known":false,"messages_allowed":false,"money_to_divide":1000000}` | alice | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=950000; median=950000 | mean=0.95; median=0.95 | 8.100000000000136 |
| `bargaining:{"complete_information":true,"delta_1":1.0,"delta_2":0.95,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":1000000}` | bob | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=635767; median=635767 | mean=0.635767; median=0.635767 | 6.349999999999909 |
| `bargaining:{"complete_information":true,"delta_1":1.0,"delta_2":1.0,"horizon_known":false,"messages_allowed":false,"money_to_divide":1000000}` | bob | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=500000; median=500000 | mean=0.5; median=0.5 | -0.009999999999990905 |
| `bargaining:{"complete_information":true,"delta_1":1.0,"delta_2":1.0,"horizon_known":true,"max_rounds":12,"messages_allowed":true,"money_to_divide":10000}` | bob | `BARGAINING_FAIRNESS` | 1 | `{"agreement":1}` | mean=9500; median=9500 | mean=0.95; median=0.95 | 7.769999999999982 |
| `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_1_value":120.0,"player_2_role":"buyer"}` | seller | `NEGOTIATION_ROBUST` | 1 | `{"walked_away":1}` | mean=0; median=0 | mean=0.5; median=0.5 | -4.8700000000000045 |
| `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_1_value":150.0,"player_2_role":"buyer"}` | seller | `NEGOTIATION_ADAPTIVE` | 1 | `{"walked_away":1}` | mean=0; median=0 | mean=0.5; median=0.5 | -2.2899999999999636 |
| `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_2_role":"buyer","player_2_value":10000.0}` | buyer | `NEGOTIATION_ROBUST` | 1 | `{"walked_away":1}` | mean=0; median=0 | mean=0.5; median=0.5 | -1.6099999999999 |
| `negotiation:{"complete_information":false,"horizon_known":false,"messages_allowed":true,"player_1_role":"seller","player_1_value":15000.0,"player_2_role":"buyer"}` | seller | `NEGOTIATION_ROBUST` | 1 | `{"walked_away":1}` | mean=0; median=0 | mean=0.5; median=0.5 | 2.689999999999941 |
| `negotiation:{"complete_information":false,"horizon_known":true,"max_rounds":10,"messages_allowed":false,"player_1_role":"seller","player_2_role":"buyer","player_2_value":1000000.0}` | buyer | `NEGOTIATION_ADAPTIVE` | 1 | `{"no_deal":1}` | mean=0; median=0 | mean=0.5; median=0.5 | -1.5300000000000864 |
| `negotiation:{"complete_information":true,"horizon_known":false,"messages_allowed":false,"player_1_role":"seller","player_1_value":120.0,"player_2_role":"buyer","player_2_value":150.0}` | buyer | `NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT` | 1 | `{"agreement":1}` | mean=15; median=15 | mean=0.525; median=0.525 | 0.01999999999998181 |
| `persuasion:{"is_seller_know_cv":false,"p":0.3333333333333333,"player_1_role":"seller","player_2_role":"buyer","product_price":100,"seller_message_type":"binary","total_rounds":20}` | seller | `PERSUASION_P0_BABBLING` | 1 | `{"completed":1}` | mean=200; median=200 | n/a | -5.720000000000027 |
| `persuasion:{"is_seller_know_cv":false,"p":0.8,"player_1_role":"seller","player_2_role":"buyer","product_price":10000,"seller_message_type":"binary","total_rounds":20}` | seller | `PERSUASION_P0_BABBLING` | 1 | `{"completed":1}` | mean=0; median=0 | n/a | -5.620000000000118 |
| `persuasion:{"is_seller_know_cv":false,"p":0.8,"player_1_role":"seller","player_2_role":"buyer","product_price":1000000,"seller_message_type":"binary","total_rounds":20,"u":0.0,"v":1250000.0}` | buyer | `PERSUASION_P0_BABBLING` | 1 | `{"completed":1}` | mean=-1.25e+06; median=-1.25e+06 | n/a | -6.069999999999936 |
| `persuasion:{"is_seller_know_cv":true,"p":0.3333333333333333,"player_1_role":"seller","player_2_role":"buyer","product_price":100,"seller_message_type":"binary","total_rounds":20,"u":0.0,"v":200.0}` | buyer | `PERSUASION_P0_BABBLING` | 1 | `{"completed":1}` | mean=0; median=0 | n/a | -2.119999999999891 |
| `persuasion:{"is_seller_know_cv":true,"p":0.8,"player_1_role":"seller","player_2_role":"buyer","product_price":10000,"seller_message_type":"binary","total_rounds":20,"u":0.0,"v":12000.0}` | seller | `PERSUASION_P0_BABBLING` | 1 | `{"completed":1}` | mean=0; median=0 | n/a | -4.110000000000127 |

## 8. Structural-class aggregates

| Structural policy class | n | Agreement/completion | No-deal | Walkaway | Raw payoff | Normalized/transformed | Rating delta | Opponents | Fallbacks | Invalid | Policy latency |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | --- | ---: | ---: | --- |
| `bargaining/COMPLETE_FINITE/complete/finite` | 1 | 0.0% | 100.0% | 0.0% | mean=0; median=0 | mean=0; median=0 | -6.810000000000173 | `{"agent":1}` | 0 | 0 | mean=0.000515743; median=0.000324312; max=0.00143421 |
| `bargaining/FAIRNESS/complete/finite` | 5 | 100.0% | 0.0% | 0.0% | mean=460148; median=635767 | mean=0.648248; median=0.655475 | 20.4699999999998 | `{"agent":3,"hidden":2}` | 0 | 0 | mean=0.00060397; median=0.000446646; max=0.00185096 |
| `bargaining/FAIRNESS/complete/unlimited` | 3 | 100.0% | 0.0% | 0.0% | mean=483347; median=500000 | mean=0.616667; median=0.5 | 12.360000000000127 | `{"hidden":3}` | 0 | 0 | mean=0.000456; median=0.000374; max=0.000665417 |
| `bargaining/FAIRNESS/incomplete` | 3 | 33.3% | 0.0% | 66.7% | mean=16.6667; median=0 | mean=0.166667; median=0 | -13.589999999999918 | `{"hidden":3}` | 0 | 0 | mean=0.000447472; median=0.000422104; max=0.000764041 |
| `bargaining/INCOMPLETE_EQUAL_SPLIT/incomplete` | 8 | 87.5% | 0.0% | 12.5% | mean=64981.2; median=4875 | mean=0.434375; median=0.5 | 6.620000000000118 | `{"agent":5,"hidden":3}` | 0 | 0 | mean=0.000610838; median=0.000522625; max=0.00123129 |
| `negotiation/ADAPTIVE/incomplete/multiround` | 1 | 0.0% | 100.0% | 0.0% | mean=0; median=0 | mean=0.5; median=0.5 | -1.5300000000000864 | `{"agent":1}` | 0 | 0 | mean=0.00101175; median=0.000928125; max=0.00190508 |
| `negotiation/ADAPTIVE/incomplete/unknown-horizon` | 1 | 0.0% | 0.0% | 100.0% | mean=0; median=0 | mean=0.5; median=0.5 | -2.2899999999999636 | `{"agent":1}` | 0 | 0 | mean=0.00104613; median=0.00076325; max=0.00270892 |
| `negotiation/COMPLETE_UNLIMITED_MIDPOINT/complete/unknown-horizon` | 1 | 100.0% | 0.0% | 0.0% | mean=15; median=15 | mean=0.525; median=0.525 | 0.01999999999998181 | `{"agent":1}` | 0 | 0 | mean=0.000378666; median=0.000378666; max=0.000378666 |
| `negotiation/ROBUST/incomplete/unknown-horizon` | 3 | 0.0% | 0.0% | 100.0% | mean=0; median=0 | mean=0.5; median=0.5 | -3.7899999999999636 | `{"agent":1,"hidden":2}` | 0 | 0 | mean=0.00098244; median=0.00079825; max=0.00351917 |
| `persuasion/P0/buyer` | 2 | 100.0% | 0.0% | 0.0% | mean=-625000; median=-625000 | n/a | -8.189999999999827 | `{"agent":2}` | 0 | 0 | mean=0.000549194; median=0.000323854; max=0.00459175 |
| `persuasion/P0/seller` | 3 | 100.0% | 0.0% | 0.0% | mean=66.6667; median=0 | n/a | -15.450000000000273 | `{"agent":1,"hidden":2}` | 0 | 0 | mean=0.000376041; median=0.000261354; max=0.00274167 |

## 9. Rating before/after

- bargaining: 1693.53 -> 1712.58.
- negotiation: 976.73 -> 969.14.
- persuasion: 1406.98 -> 1383.34.

## 10. Stop-loss evaluation

- bargaining: operational stops=0; class pauses=2; `PAUSE_AND_REDESIGN` (strategic class pauses=2).
  - paused `bargaining/FAIRNESS/incomplete`: `NON_UNAVOIDABLE_ZERO_NO_DEAL_OR_WALKAWAY_RATE_ABOVE_HALF`.
  - paused `bargaining/FAIRNESS/complete/finite`: `BARGAINING_FAIRNESS_NOT_ABOVE_THEORY_IN_FOUR_OF_FIRST_FIVE`.
- negotiation: operational stops=0; class pauses=3; `PAUSE_AND_REDESIGN` (strategic class pauses=3).
  - paused `negotiation/ADAPTIVE/incomplete/unknown-horizon`: `ADAPTIVE_REPEATEDLY_IGNORED_MATERIALLY_IMPROVING_OFFERS`.
  - paused `negotiation/ADAPTIVE/incomplete/multiround`: `ADAPTIVE_REPEATEDLY_IGNORED_MATERIALLY_IMPROVING_OFFERS`.
  - paused `negotiation/ROBUST/incomplete/unknown-horizon`: `FIRST_THREE_OBSERVATIONS_ALL_ZERO_OWN_PAYOFF`.
- persuasion: operational stops=0; class pauses=1; `PAUSE_AND_REDESIGN` (strategic class pauses=1).
  - paused `persuasion/P0/seller`: `NON_UNAVOIDABLE_ZERO_NO_DEAL_OR_WALKAWAY_RATE_ABOVE_HALF`.

## 11. Challenger-specific results

- NEGOTIATION_ADAPTIVE diagnostic: n=2; agreement/completion=0.0%; raw mean=0; median=0; normalized/transformed mean=0.5; median=0.5.
- NEGOTIATION_ROBUST comparison slice: n=3; agreement/completion=0.0%; raw mean=0; median=0; normalized/transformed mean=0.5; median=0.5.
- NEGOTIATION_FAIRNESS_MARGIN: n=0; agreement/completion=n/a; raw n/a; normalized/transformed n/a.
- BARGAINING_FAIRNESS: n=11; agreement/completion=81.8%; raw mean=340985; median=50000; normalized/transformed mean=0.508295; median=0.5.
- `NEGOTIATION_ADAPTIVE`: `PAUSE_AND_REDESIGN`. Both observed eligible structural
  classes triggered the improving-offer rule. The diagnostic is nonrandom and does not
  establish causal superiority.
- `NEGOTIATION_ROBUST` in incomplete unknown-horizon cells: `PAUSE_AND_REDESIGN` after
  its first three observations all produced zero own payoff/walkaway.
- `NEGOTIATION_FAIRNESS_MARGIN`: `LIMITED_DEPLOYMENT_ONLY`; matchmaking produced zero
  applicable complete finite extraction cells, so it was not exercised in this tranche.
- `NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT`: `LIMITED_DEPLOYMENT_ONLY`; its one observed
  match agreed, but the family queue cannot be restricted to that structural class.
- `BARGAINING_FAIRNESS`: `PAUSE_AND_REDESIGN`; incomplete FAIRNESS and complete finite
  FAIRNESS each hit a predeclared stop-loss.
- `BARGAINING_INCOMPLETE_EQUAL_SPLIT` and the exact complete finite bargaining theory
  incumbent: `LIMITED_DEPLOYMENT_ONLY`; neither triggered within its observed slice, but
  family matchmaking cannot exclude the paused FAIRNESS classes.
- `PERSUASION_P0_BABBLING`: `PAUSE_AND_REDESIGN`; its seller structural class exceeded
  the zero-payoff stop threshold. P3 was selected zero times and remains
  `RESEARCH_BLOCKED` because its required population input is unavailable.

## 12. Failures, fallbacks, timeouts, and shutdown

- bargaining: fallback=0; invalid=0; timeout=0; active=0; pending=0.
- negotiation: fallback=0; invalid=0; timeout=0; active=0; pending=0.
- persuasion: fallback=0; invalid=0; timeout=0; active=0; pending=0.

## 13. Classification and technical recommendation

- bargaining: `PAUSE_AND_REDESIGN`.
- negotiation: `PAUSE_AND_REDESIGN`.
- persuasion: `PAUSE_AND_REDESIGN`.

No family cleared the precommitted sustained-deployment rule, so the exact current
production recommendation is: **do not start sustained execution for any family**.
`docs/leaderboard_tranche_plan.md` remains the historical frozen map that was actually
tested; its paused classes must not be silently re-enabled. A future authorized map must
address the recorded structural failures and preserve the untriggered incumbents rather
than using rating movement as an override.

No sustained execution was started. All queues were stopped pending explicit human authorization.

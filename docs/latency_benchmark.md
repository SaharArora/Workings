# Production policy latency benchmark

Authoritative turn limit: **120s**. Internal budgets: p95 <= **10s**, maximum <= **30s**. Measurements include envelope parsing, routing and policy computation, communication rendering, and local action validation. Network/API time is excluded.

| Path | Family | Selected policy | n | Median (ms) | p95 (ms) | Max (ms) | Budget |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `negotiation.complete.t1` | negotiation | `NEGOTIATION_COMPLETE_T1_THEORY` | 1000 | 0.0125 | 0.0163 | 1.4298 | PASS |
| `negotiation.complete.finite_odd` | negotiation | `NEGOTIATION_COMPLETE_FINITE_ODD_THEORY` | 1000 | 0.0124 | 0.0306 | 1.2875 | PASS |
| `negotiation.complete.finite_even` | negotiation | `NEGOTIATION_COMPLETE_FINITE_EVEN_THEORY` | 1000 | 0.0132 | 0.0169 | 0.1916 | PASS |
| `negotiation.complete.unlimited` | negotiation | `NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT` | 1000 | 0.0124 | 0.0146 | 0.5142 | PASS |
| `negotiation.incomplete.t1.robust` | negotiation | `NEGOTIATION_INCOMPLETE_T1_ROBUST` | 1000 | 0.0623 | 0.1007 | 0.3003 | PASS |
| `negotiation.incomplete.finite.robust` | negotiation | `NEGOTIATION_ROBUST` | 1000 | 0.0701 | 0.1395 | 0.6045 | PASS |
| `negotiation.incomplete.unlimited.robust` | negotiation | `NEGOTIATION_ROBUST` | 1000 | 0.0592 | 0.0869 | 0.1992 | PASS |
| `bargaining.complete.finite` | bargaining | `BARGAINING_COMPLETE_FINITE` | 1000 | 0.0128 | 0.0140 | 0.0869 | PASS |
| `bargaining.complete.unlimited` | bargaining | `BARGAINING_COMPLETE_UNLIMITED` | 1000 | 0.0117 | 0.0139 | 0.0723 | PASS |
| `bargaining.incomplete.finite.equal_split` | bargaining | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 1000 | 0.0123 | 0.0133 | 0.6747 | PASS |
| `bargaining.incomplete.unlimited.equal_split` | bargaining | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 1000 | 0.0124 | 0.0135 | 0.6840 | PASS |
| `persuasion.p0.seller_text` | persuasion | `PERSUASION_P0_BABBLING` | 1000 | 0.0106 | 0.0109 | 0.5795 | PASS |
| `persuasion.p0.seller_binary` | persuasion | `PERSUASION_P0_BABBLING` | 1000 | 0.0112 | 0.0118 | 0.4310 | PASS |
| `persuasion.p0.buyer` | persuasion | `PERSUASION_P0_BABBLING` | 1000 | 0.0119 | 0.0125 | 0.1677 | PASS |

# Production policy latency benchmark

Authoritative turn limit: **120s**. Internal budgets: p95 <= **10s**, maximum <= **30s**. Measurements include envelope parsing, routing and policy computation, communication rendering, and local action validation. Network/API time is excluded.

| Path | Family | Selected policy | n | Median (ms) | p95 (ms) | Max (ms) | Budget |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `negotiation.complete.t1` | negotiation | `NEGOTIATION_COMPLETE_T1_THEORY` | 1000 | 0.0125 | 0.0132 | 0.1439 | PASS |
| `negotiation.complete.finite_odd` | negotiation | `NEGOTIATION_COMPLETE_FINITE_ODD_THEORY` | 1000 | 0.0120 | 0.0125 | 0.1762 | PASS |
| `negotiation.complete.finite_even` | negotiation | `NEGOTIATION_COMPLETE_FINITE_EVEN_THEORY` | 1000 | 0.0128 | 0.0133 | 0.2465 | PASS |
| `negotiation.complete.unlimited` | negotiation | `NEGOTIATION_COMPLETE_UNLIMITED_MIDPOINT` | 1000 | 0.0122 | 0.0129 | 0.1270 | PASS |
| `negotiation.incomplete.t1.robust` | negotiation | `NEGOTIATION_INCOMPLETE_T1_ROBUST` | 1000 | 0.0605 | 0.0678 | 0.3449 | PASS |
| `negotiation.incomplete.finite.robust` | negotiation | `NEGOTIATION_ROBUST` | 1000 | 0.0667 | 0.0755 | 0.2580 | PASS |
| `negotiation.incomplete.unlimited.robust` | negotiation | `NEGOTIATION_ROBUST` | 1000 | 0.0632 | 0.1145 | 0.5600 | PASS |
| `bargaining.complete.finite` | bargaining | `BARGAINING_COMPLETE_FINITE` | 1000 | 0.0142 | 0.0491 | 0.2824 | PASS |
| `bargaining.complete.unlimited` | bargaining | `BARGAINING_COMPLETE_UNLIMITED` | 1000 | 0.0128 | 0.0408 | 0.3669 | PASS |
| `bargaining.incomplete.finite.equal_split` | bargaining | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 1000 | 0.0127 | 0.0292 | 0.2007 | PASS |
| `bargaining.incomplete.unlimited.equal_split` | bargaining | `BARGAINING_INCOMPLETE_EQUAL_SPLIT` | 1000 | 0.0126 | 0.0422 | 0.3343 | PASS |
| `persuasion.p0.seller_text` | persuasion | `PERSUASION_P0_BABBLING` | 1000 | 0.0110 | 0.0215 | 0.2801 | PASS |
| `persuasion.p0.seller_binary` | persuasion | `PERSUASION_P0_BABBLING` | 1000 | 0.0117 | 0.0239 | 0.2818 | PASS |
| `persuasion.p0.buyer` | persuasion | `PERSUASION_P0_BABBLING` | 1000 | 0.0128 | 0.0323 | 0.3033 | PASS |

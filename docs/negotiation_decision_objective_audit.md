# Negotiation decision-objective audit

This audit was frozen before the pooled selector was modified. It uses the already-consumed response-model test split only to diagnose the old decision objective; it is not the fresh risk-selector holdout.

## Exact old objective

For candidate `a`, the implementation scored:

```text
S_old(a) = q_accept(a) * U_accept(a) + (1-q_accept(a)) * V_old

V_old = 0                                      on action_type=offer
V_old = 0.25*q_accept(ROBUST)*U_accept(ROBUST) on a nonterminal counter
```

`V_old` was constant across all candidates in a counter state. At a terminal response without a legal counter, the empirical selector did not score candidates and delegated to ROBUST's IR-safe terminal response.

**Classification: `CONTINUATION_TERM_PRESENT_BUT_MISSPECIFIED`.** The term existed, but it was zero on genuinely nonterminal opening offers, candidate-independent on counters, did not distinguish continuation from terminal nonagreement, and provided neither a payoff distribution nor a lower-tail/no-deal calculation. It was therefore not a valid candidate-specific continuation approximation.

## Representative state construction

The 20 states below were selected deterministically by SHA-256 priority, round-robin across role, information, known/unknown horizon, opponent category, and inferred offer/counter context. They come from the previously consumed test split and cover the old objective only.

## Candidate-by-candidate decomposition

| State | Cell/context | Candidate | q(accept) | Accept payoff | P(nonaccept) | Old continuation | Rejection contribution | Total old score | Selected |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 3750.000000 | 0.685238 | 11250.000000 | 0.314762 | 1383.440330 | 435.454117 | 8144.384284 | yes |
| 1 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 7500.000000 | 0.737835 | 7500.000000 | 0.262165 | 1383.440330 | 362.689852 | 5896.451171 |  |
| 1 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 9750.000000 | 0.766530 | 5250.000000 | 0.233470 | 1383.440330 | 322.991326 | 4347.275677 |  |
| 1 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 11250.000000 | 0.784408 | 3750.000000 | 0.215592 | 1383.440330 | 298.259000 | 3239.788099 |  |
| 1 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 12000.000000 | 0.792966 | 3000.000000 | 0.207034 | 1383.440330 | 286.418779 | 2665.317659 |  |
| 1 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 13500.000000 | 0.809323 | 1500.000000 | 0.190677 | 1383.440330 | 263.790289 | 1477.774749 |  |
| 1 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 15000.000000 | 0.921409 | 0.000000 | 0.078591 | 1383.440330 | 108.725957 | 108.725957 |  |
| 2 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 2500.000000 | 0.210874 | 7500.000000 | 0.789126 | 320.951619 | 253.271269 | 1834.826234 | yes |
| 2 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 5000.000000 | 0.256761 | 5000.000000 | 0.743239 | 320.951619 | 238.543665 | 1522.350140 |  |
| 2 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 5700.000000 | 0.270721 | 4300.000000 | 0.729279 | 320.951619 | 234.063293 | 1398.163360 |  |
| 2 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 7500.000000 | 0.308727 | 2500.000000 | 0.691273 | 320.951619 | 221.865064 | 993.683533 |  |
| 2 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 9500.000000 | 0.359896 | 500.000000 | 0.640104 | 320.951619 | 205.442425 | 385.390409 |  |
| 2 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 10000.000000 | 0.377627 | 0.000000 | 0.622373 | 320.951619 | 199.751623 | 199.751623 |  |
| 3 | `buyer|complete|unknown|llm / NONTERMINAL_COUNTER` | 250000.000000 | 0.254950 | 750000.000000 | 0.745050 | 38337.660879 | 28563.456811 | 219776.297743 | yes |
| 3 | `buyer|complete|unknown|llm / NONTERMINAL_COUNTER` | 500000.000000 | 0.306701 | 500000.000000 | 0.693299 | 38337.660879 | 26579.450946 | 179930.094464 |  |
| 3 | `buyer|complete|unknown|llm / NONTERMINAL_COUNTER` | 535000.000000 | 0.314398 | 465000.000000 | 0.685602 | 38337.660879 | 26284.358990 | 172479.647118 |  |
| 3 | `buyer|complete|unknown|llm / NONTERMINAL_COUNTER` | 750000.000000 | 0.363827 | 250000.000000 | 0.636173 | 38337.660879 | 24389.383097 | 115346.143774 |  |
| 3 | `buyer|complete|unknown|llm / NONTERMINAL_COUNTER` | 800000.000000 | 0.375796 | 200000.000000 | 0.624204 | 38337.660879 | 23930.540318 | 99089.640956 |  |
| 3 | `buyer|complete|unknown|llm / NONTERMINAL_COUNTER` | 950000.000000 | 0.418598 | 50000.000000 | 0.581402 | 38337.660879 | 22289.597946 | 43219.491118 |  |
| 3 | `buyer|complete|unknown|llm / NONTERMINAL_COUNTER` | 1000000.000000 | 0.437245 | 0.000000 | 0.562755 | 38337.660879 | 21574.693728 | 21574.693728 |  |
| 4 | `buyer|incomplete|known|human / NONTERMINAL_COUNTER` | 375000.000000 | 0.799967 | 1125000.000000 | 0.200033 | 157111.269426 | 31427.450864 | 931390.237739 | yes |
| 4 | `buyer|incomplete|known|human / NONTERMINAL_COUNTER` | 750000.000000 | 0.837927 | 750000.000000 | 0.162073 | 157111.269426 | 25463.530862 | 653908.608567 |  |
| 4 | `buyer|incomplete|known|human / NONTERMINAL_COUNTER` | 875000.000000 | 0.849218 | 625000.000000 | 0.150782 | 157111.269426 | 23689.554040 | 554450.793645 |  |
| 4 | `buyer|incomplete|known|human / NONTERMINAL_COUNTER` | 1000000.000000 | 0.859854 | 500000.000000 | 0.140146 | 157111.269426 | 22018.494964 | 451945.561798 |  |
| 4 | `buyer|incomplete|known|human / NONTERMINAL_COUNTER` | 1125000.000000 | 0.869855 | 375000.000000 | 0.130145 | 157111.269426 | 20447.247372 | 346642.869479 |  |
| 4 | `buyer|incomplete|known|human / NONTERMINAL_COUNTER` | 1500000.000000 | 0.955629 | 0.000000 | 0.044371 | 157111.269426 | 6971.182140 | 6971.182140 |  |
| 5 | `buyer|incomplete|known|llm / NONTERMINAL_COUNTER` | 20.000000 | 0.022633 | 60.000000 | 0.977367 | 0.290665 | 0.284086 | 1.642048 | yes |
| 5 | `buyer|incomplete|known|llm / NONTERMINAL_COUNTER` | 40.000000 | 0.029066 | 40.000000 | 0.970934 | 0.290665 | 0.282216 | 1.444876 |  |
| 5 | `buyer|incomplete|known|llm / NONTERMINAL_COUNTER` | 50.000000 | 0.032918 | 30.000000 | 0.967082 | 0.290665 | 0.281097 | 1.268626 |  |
| 5 | `buyer|incomplete|known|llm / NONTERMINAL_COUNTER` | 60.000000 | 0.037259 | 20.000000 | 0.962741 | 0.290665 | 0.279835 | 1.025025 |  |
| 5 | `buyer|incomplete|known|llm / NONTERMINAL_COUNTER` | 80.000000 | 0.110881 | 0.000000 | 0.889119 | 0.290665 | 0.258436 | 0.258436 |  |
| 6 | `buyer|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 20.000000 | 0.265898 | 60.000000 | 0.734102 | 3.189193 | 2.341194 | 18.295045 | yes |
| 6 | `buyer|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 40.000000 | 0.318919 | 40.000000 | 0.681081 | 3.189193 | 2.172098 | 14.928868 |  |
| 6 | `buyer|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 60.000000 | 0.377083 | 20.000000 | 0.622917 | 3.189193 | 1.986602 | 9.528262 |  |
| 6 | `buyer|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 64.500000 | 0.390748 | 15.500000 | 0.609252 | 3.189193 | 1.943022 | 7.999615 |  |
| 6 | `buyer|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 75.000000 | 0.438490 | 5.000000 | 0.561510 | 3.189193 | 1.790763 | 3.983214 |  |
| 6 | `buyer|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 80.000000 | 0.462057 | 0.000000 | 0.537943 | 3.189193 | 1.715603 | 1.715603 |  |
| 7 | `seller|complete|known|human / NONTERMINAL_COUNTER` | 12000.000000 | 0.684057 | 0.000000 | 0.315943 | 939.706586 | 296.893878 | 296.893878 |  |
| 7 | `seller|complete|known|human / NONTERMINAL_COUNTER` | 13000.000000 | 0.655823 | 1000.000000 | 0.344177 | 939.706586 | 323.425739 | 979.248371 |  |
| 7 | `seller|complete|known|human / NONTERMINAL_COUNTER` | 13200.000000 | 0.650033 | 1200.000000 | 0.349967 | 939.706586 | 328.866316 | 1108.905889 |  |
| 7 | `seller|complete|known|human / NONTERMINAL_COUNTER` | 14000.000000 | 0.730387 | 2000.000000 | 0.269613 | 939.706586 | 253.356721 | 1714.131552 |  |
| 7 | `seller|complete|known|human / NONTERMINAL_COUNTER` | 15000.000000 | 0.626450 | 3000.000000 | 0.373550 | 939.706586 | 351.027272 | 2230.377665 |  |
| 7 | `seller|complete|known|human / NONTERMINAL_COUNTER` | 18000.000000 | 0.626471 | 6000.000000 | 0.373529 | 939.706586 | 351.007608 | 4109.833950 |  |
| 7 | `seller|complete|known|human / NONTERMINAL_COUNTER` | 24000.000000 | 0.626513 | 12000.000000 | 0.373487 | 939.706586 | 350.968280 | 7869.123176 | yes |
| 8 | `seller|complete|known|human / NONTERMINAL_OFFER` | 10000.000000 | 0.832588 | 0.000000 | 0.167412 | 0.000000 | 0.000000 | 0.000000 |  |
| 8 | `seller|complete|known|human / NONTERMINAL_OFFER` | 11000.000000 | 0.754825 | 1000.000000 | 0.245175 | 0.000000 | 0.000000 | 754.825404 |  |
| 8 | `seller|complete|known|human / NONTERMINAL_OFFER` | 11500.000000 | 0.754829 | 1500.000000 | 0.245171 | 0.000000 | 0.000000 | 1132.243070 |  |
| 8 | `seller|complete|known|human / NONTERMINAL_OFFER` | 12500.000000 | 0.754835 | 2500.000000 | 0.245165 | 0.000000 | 0.000000 | 1887.088333 |  |
| 8 | `seller|complete|known|human / NONTERMINAL_OFFER` | 15000.000000 | 0.754852 | 5000.000000 | 0.245148 | 0.000000 | 0.000000 | 3774.259409 |  |
| 8 | `seller|complete|known|human / NONTERMINAL_OFFER` | 20000.000000 | 0.754885 | 10000.000000 | 0.245115 | 0.000000 | 0.000000 | 7548.849765 | yes |
| 9 | `seller|complete|known|llm / NONTERMINAL_COUNTER` | 80.000000 | 0.286004 | 0.000000 | 0.713996 | 2.557790 | 1.826252 | 1.826252 |  |
| 9 | `seller|complete|known|llm / NONTERMINAL_COUNTER` | 85.000000 | 0.266846 | 5.000000 | 0.733154 | 2.557790 | 1.875253 | 3.209485 |  |
| 9 | `seller|complete|known|llm / NONTERMINAL_COUNTER` | 86.000000 | 0.263114 | 6.000000 | 0.736886 | 2.557790 | 1.884799 | 3.463485 |  |
| 9 | `seller|complete|known|llm / NONTERMINAL_COUNTER` | 88.000000 | 0.356964 | 8.000000 | 0.643036 | 2.557790 | 1.644751 | 4.500462 |  |
| 9 | `seller|complete|known|llm / NONTERMINAL_COUNTER` | 100.000000 | 0.255762 | 20.000000 | 0.744238 | 2.557790 | 1.903604 | 7.018844 |  |
| 9 | `seller|complete|known|llm / NONTERMINAL_COUNTER` | 102.500000 | 0.255764 | 22.500000 | 0.744236 | 2.557790 | 1.903599 | 7.658291 |  |
| 9 | `seller|complete|known|llm / NONTERMINAL_COUNTER` | 120.000000 | 0.255779 | 40.000000 | 0.744221 | 2.557790 | 1.903561 | 12.134720 |  |
| 9 | `seller|complete|known|llm / NONTERMINAL_COUNTER` | 160.000000 | 0.255813 | 80.000000 | 0.744187 | 2.557790 | 1.903474 | 22.368516 | yes |
| 10 | `seller|complete|known|llm / NONTERMINAL_OFFER` | 12000.000000 | 0.233325 | 0.000000 | 0.766675 | 0.000000 | 0.000000 | 0.000000 |  |
| 10 | `seller|complete|known|llm / NONTERMINAL_OFFER` | 13200.000000 | 0.158532 | 1200.000000 | 0.841468 | 0.000000 | 0.000000 | 190.238078 |  |
| 10 | `seller|complete|known|llm / NONTERMINAL_OFFER` | 15000.000000 | 0.158539 | 3000.000000 | 0.841461 | 0.000000 | 0.000000 | 475.616667 |  |
| 10 | `seller|complete|known|llm / NONTERMINAL_OFFER` | 16000.000000 | 0.158543 | 4000.000000 | 0.841457 | 0.000000 | 0.000000 | 634.171463 |  |
| 10 | `seller|complete|known|llm / NONTERMINAL_OFFER` | 18000.000000 | 0.158551 | 6000.000000 | 0.841449 | 0.000000 | 0.000000 | 951.304915 |  |
| 10 | `seller|complete|known|llm / NONTERMINAL_OFFER` | 24000.000000 | 0.158575 | 12000.000000 | 0.841425 | 0.000000 | 0.000000 | 1902.896177 | yes |
| 11 | `seller|complete|unknown|llm / NONTERMINAL_COUNTER` | 1200000.000000 | 0.377541 | 0.000000 | 0.622459 | 45888.201359 | 28563.518781 | 28563.518781 |  |
| 11 | `seller|complete|unknown|llm / NONTERMINAL_COUNTER` | 1300000.000000 | 0.348022 | 100000.000000 | 0.651978 | 45888.201359 | 29918.080951 | 64720.317550 |  |
| 11 | `seller|complete|unknown|llm / NONTERMINAL_COUNTER` | 1320000.000000 | 0.342248 | 120000.000000 | 0.657752 | 45888.201359 | 30183.058793 | 71252.812065 |  |
| 11 | `seller|complete|unknown|llm / NONTERMINAL_COUNTER` | 1375000.000000 | 0.326611 | 175000.000000 | 0.673389 | 45888.201359 | 30900.602416 | 88057.556435 |  |
| 11 | `seller|complete|unknown|llm / NONTERMINAL_COUNTER` | 1500000.000000 | 0.305902 | 300000.000000 | 0.694098 | 45888.201359 | 31850.892505 | 123621.598949 |  |
| 11 | `seller|complete|unknown|llm / NONTERMINAL_COUNTER` | 1550000.000000 | 0.305906 | 350000.000000 | 0.694094 | 45888.201359 | 31850.747290 | 138917.679067 |  |
| 11 | `seller|complete|unknown|llm / NONTERMINAL_COUNTER` | 1800000.000000 | 0.305921 | 600000.000000 | 0.694079 | 45888.201359 | 31850.021199 | 215402.826635 |  |
| 11 | `seller|complete|unknown|llm / NONTERMINAL_COUNTER` | 2400000.000000 | 0.305959 | 1200000.000000 | 0.694041 | 45888.201359 | 31848.278497 | 398999.461935 | yes |
| 12 | `seller|complete|unknown|llm / NONTERMINAL_OFFER` | 100.000000 | 0.439564 | 0.000000 | 0.560436 | 0.000000 | 0.000000 | 0.000000 |  |
| 12 | `seller|complete|unknown|llm / NONTERMINAL_OFFER` | 110.000000 | 0.326844 | 10.000000 | 0.673156 | 0.000000 | 0.000000 | 3.268435 |  |
| 12 | `seller|complete|unknown|llm / NONTERMINAL_OFFER` | 125.000000 | 0.326855 | 25.000000 | 0.673145 | 0.000000 | 0.000000 | 8.171383 |  |
| 12 | `seller|complete|unknown|llm / NONTERMINAL_OFFER` | 140.000000 | 0.326867 | 40.000000 | 0.673133 | 0.000000 | 0.000000 | 13.074685 |  |
| 12 | `seller|complete|unknown|llm / NONTERMINAL_OFFER` | 150.000000 | 0.326875 | 50.000000 | 0.673125 | 0.000000 | 0.000000 | 16.343750 |  |
| 12 | `seller|complete|unknown|llm / NONTERMINAL_OFFER` | 200.000000 | 0.326914 | 100.000000 | 0.673086 | 0.000000 | 0.000000 | 32.691436 | yes |
| 13 | `seller|incomplete|known|human / NONTERMINAL_COUNTER` | 150.000000 | 0.908372 | 0.000000 | 0.091628 | 16.051253 | 1.470739 | 1.470739 |  |
| 13 | `seller|incomplete|known|human / NONTERMINAL_COUNTER` | 162.500000 | 0.897171 | 12.500000 | 0.102829 | 16.051253 | 1.650539 | 12.865173 |  |
| 13 | `seller|incomplete|known|human / NONTERMINAL_COUNTER` | 165.000000 | 0.894790 | 15.000000 | 0.105210 | 16.051253 | 1.688758 | 15.110603 |  |
| 13 | `seller|incomplete|known|human / NONTERMINAL_COUNTER` | 175.000000 | 0.884773 | 25.000000 | 0.115227 | 16.051253 | 1.849532 | 23.968866 |  |
| 13 | `seller|incomplete|known|human / NONTERMINAL_COUNTER` | 187.500000 | 0.871096 | 37.500000 | 0.128904 | 16.051253 | 2.069069 | 34.735173 |  |
| 13 | `seller|incomplete|known|human / NONTERMINAL_COUNTER` | 225.000000 | 0.856067 | 75.000000 | 0.143933 | 16.051253 | 2.310308 | 66.515320 |  |
| 13 | `seller|incomplete|known|human / NONTERMINAL_COUNTER` | 300.000000 | 0.856089 | 150.000000 | 0.143911 | 16.051253 | 2.309954 | 130.723285 | yes |
| 14 | `seller|incomplete|known|human / NONTERMINAL_OFFER` | 800000.000000 | 0.964306 | 0.000000 | 0.035694 | 0.000000 | 0.000000 | 0.000000 |  |
| 14 | `seller|incomplete|known|human / NONTERMINAL_OFFER` | 880000.000000 | 0.943580 | 80000.000000 | 0.056420 | 0.000000 | 0.000000 | 75486.433269 |  |
| 14 | `seller|incomplete|known|human / NONTERMINAL_OFFER` | 1000000.000000 | 0.943583 | 200000.000000 | 0.056417 | 0.000000 | 0.000000 | 188716.654439 |  |
| 14 | `seller|incomplete|known|human / NONTERMINAL_OFFER` | 1200000.000000 | 0.943588 | 400000.000000 | 0.056412 | 0.000000 | 0.000000 | 377435.212977 |  |
| 14 | `seller|incomplete|known|human / NONTERMINAL_OFFER` | 1600000.000000 | 0.943598 | 800000.000000 | 0.056402 | 0.000000 | 0.000000 | 754878.041445 | yes |
| 15 | `seller|incomplete|known|llm / NONTERMINAL_COUNTER` | 800000.000000 | 0.439105 | 0.000000 | 0.560895 | 37012.864750 | 20760.318121 | 20760.318121 |  |
| 15 | `seller|incomplete|known|llm / NONTERMINAL_COUNTER` | 880000.000000 | 0.401772 | 80000.000000 | 0.598228 | 37012.864750 | 22142.141457 | 54283.881132 |  |
| 15 | `seller|incomplete|known|llm / NONTERMINAL_COUNTER` | 1000000.000000 | 0.347957 | 200000.000000 | 0.652043 | 37012.864750 | 24133.965580 | 93725.440095 |  |
| 15 | `seller|incomplete|known|llm / NONTERMINAL_COUNTER` | 1100000.000000 | 0.305838 | 300000.000000 | 0.694162 | 37012.864750 | 25692.910405 | 117444.422381 |  |
| 15 | `seller|incomplete|known|llm / NONTERMINAL_COUNTER` | 1150000.000000 | 0.285884 | 350000.000000 | 0.714116 | 37012.864750 | 26431.462466 | 126491.018092 |  |
| 15 | `seller|incomplete|known|llm / NONTERMINAL_COUNTER` | 1200000.000000 | 0.370129 | 400000.000000 | 0.629871 | 37012.864750 | 23313.343180 | 171364.802180 |  |
| 15 | `seller|incomplete|known|llm / NONTERMINAL_COUNTER` | 1600000.000000 | 0.266767 | 800000.000000 | 0.733233 | 37012.864750 | 27139.049477 | 240552.744200 | yes |
| 16 | `seller|incomplete|known|llm / NONTERMINAL_OFFER` | 80.000000 | 0.260191 | 0.000000 | 0.739809 | 0.000000 | 0.000000 | 0.000000 |  |
| 16 | `seller|incomplete|known|llm / NONTERMINAL_OFFER` | 88.000000 | 0.178793 | 8.000000 | 0.821207 | 0.000000 | 0.000000 | 1.430347 |  |
| 16 | `seller|incomplete|known|llm / NONTERMINAL_OFFER` | 100.000000 | 0.178801 | 20.000000 | 0.821199 | 0.000000 | 0.000000 | 3.576026 |  |
| 16 | `seller|incomplete|known|llm / NONTERMINAL_OFFER` | 120.000000 | 0.178814 | 40.000000 | 0.821186 | 0.000000 | 0.000000 | 7.152576 |  |
| 16 | `seller|incomplete|known|llm / NONTERMINAL_OFFER` | 160.000000 | 0.178841 | 80.000000 | 0.821159 | 0.000000 | 0.000000 | 14.307254 | yes |
| 17 | `seller|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 12000.000000 | 0.189025 | 0.000000 | 0.810975 | 205.665033 | 166.789162 | 166.789162 |  |
| 17 | `seller|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 13200.000000 | 0.166637 | 1200.000000 | 0.833363 | 205.665033 | 171.393620 | 371.358071 |  |
| 17 | `seller|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 13500.000000 | 0.161383 | 1500.000000 | 0.838617 | 205.665033 | 172.474225 | 414.548490 |  |
| 17 | `seller|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 15000.000000 | 0.204242 | 3000.000000 | 0.795758 | 205.665033 | 163.659668 | 776.384601 |  |
| 17 | `seller|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 18000.000000 | 0.137110 | 6000.000000 | 0.862890 | 205.665033 | 177.466296 | 1000.126427 |  |
| 17 | `seller|incomplete|unknown|llm / NONTERMINAL_COUNTER` | 24000.000000 | 0.137131 | 12000.000000 | 0.862869 | 205.665033 | 177.461944 | 1823.036142 | yes |
| 18 | `seller|incomplete|unknown|llm / NONTERMINAL_OFFER` | 120.000000 | 0.515636 | 0.000000 | 0.484364 | 0.000000 | 0.000000 | 0.000000 |  |
| 18 | `seller|incomplete|unknown|llm / NONTERMINAL_OFFER` | 132.000000 | 0.397235 | 12.000000 | 0.602765 | 0.000000 | 0.000000 | 4.766814 |  |
| 18 | `seller|incomplete|unknown|llm / NONTERMINAL_OFFER` | 150.000000 | 0.397247 | 30.000000 | 0.602753 | 0.000000 | 0.000000 | 11.917421 |  |
| 18 | `seller|incomplete|unknown|llm / NONTERMINAL_OFFER` | 180.000000 | 0.397269 | 60.000000 | 0.602731 | 0.000000 | 0.000000 | 23.836126 |  |
| 18 | `seller|incomplete|unknown|llm / NONTERMINAL_OFFER` | 240.000000 | 0.397312 | 120.000000 | 0.602688 | 0.000000 | 0.000000 | 47.677392 | yes |
| 19 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 3000.000000 | 0.673785 | 9000.000000 | 0.326215 | 1091.301688 | 355.998978 | 6420.063994 | yes |
| 19 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 6000.000000 | 0.727534 | 6000.000000 | 0.272466 | 1091.301688 | 297.342105 | 4662.548857 |  |
| 19 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 8500.000000 | 0.767838 | 3500.000000 | 0.232162 | 1091.301688 | 253.358488 | 2940.792433 |  |
| 19 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 9000.000000 | 0.775380 | 3000.000000 | 0.224620 | 1091.301688 | 245.128019 | 2571.268475 |  |
| 19 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 9500.000000 | 0.782746 | 2500.000000 | 0.217254 | 1091.301688 | 237.089271 | 2193.955155 |  |
| 19 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 11000.000000 | 0.803788 | 1000.000000 | 0.196212 | 1091.301688 | 214.126364 | 1017.914477 |  |
| 19 | `buyer|complete|known|human / NONTERMINAL_COUNTER` | 12000.000000 | 0.917515 | 0.000000 | 0.082485 | 1091.301688 | 90.016164 | 90.016164 |  |
| 20 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 3000.000000 | 0.182951 | 9000.000000 | 0.817049 | 336.736730 | 275.130267 | 1921.693054 | yes |
| 20 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 6000.000000 | 0.224491 | 6000.000000 | 0.775509 | 336.736730 | 261.142313 | 1608.089235 |  |
| 20 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 6175.000000 | 0.227110 | 5825.000000 | 0.772890 | 336.736730 | 260.260519 | 1583.175106 |  |
| 20 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 8250.000000 | 0.259785 | 3750.000000 | 0.740215 | 336.736730 | 249.257622 | 1223.450893 |  |
| 20 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 9000.000000 | 0.482613 | 3000.000000 | 0.517387 | 336.736730 | 174.223234 | 1622.061990 |  |
| 20 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 10000.000000 | 0.298193 | 2000.000000 | 0.701807 | 336.736730 | 236.324128 | 832.710525 |  |
| 20 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 10500.000000 | 0.311647 | 1500.000000 | 0.688353 | 336.736730 | 231.793742 | 699.264227 |  |
| 20 | `buyer|complete|known|llm / NONTERMINAL_COUNTER` | 12000.000000 | 0.353892 | 0.000000 | 0.646108 | 336.736730 | 217.568159 | 217.568159 |  |

The selected endpoint/long-shot offers are a decision-objective result. No response-model coefficient, feature, calibration parameter, or artifact version is changed by this audit.

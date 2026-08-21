# Historical data

The source is the public [`eilamshapira/GLEE`](https://github.com/eilamshapira/GLEE)
repository, branch `master`, under `Data/`. Raw data is intentionally excluded from Git.
The observed layout is:

```text
Data/<human_vs_llm|llm_vs_llm>/<family>/<hex shards...>/<game id>/
  config.json
  game.csv
```

Targeted negotiation ingestion is incremental and does not require the other families:

```bash
uv run python scripts/ingest_historical.py /path/to/Data/human_vs_llm/negotiation \
  --stratum human_vs_llm --output data/processed/human_negotiation.jsonl
```

Generated records and raw data are ignored. `config.json` determines an exact cell;
`game.csv` contains ordered offer/decision rows. Additional strata and families can be
added without changing the normalized per-game envelope.

## Targeted negotiation profile (2026-08-21)

`human_vs_llm/negotiation` was fully ingested: 1,224 games in 2,448 files, 1,541,404
logical bytes (9,792 KiB on disk), parsed in 0.61 seconds. It contained 30 exact cells;
counts ranged from 30 to 102 games. Therefore no exact `(cell, opponent-category)`
stratum reaches the locked `n >= 200` BAYES gate.

Snapshot SHA-256:
`d53a06167b625c80fe3c7c9e3dee606c0c67bec693cf4edb968e552586e5b6d9`.

The `llm_vs_llm/negotiation` recursive GitHub tree was truncated at 80,454 entries; its
returned prefix already contained 55,852 blobs and 47,408,482 bytes. Two targeted sparse
Git fetches failed at the public promisor remote with HTTP 400. That source remains
incrementally ingestible by the same code after acquisition, but is not represented in
the current profile.

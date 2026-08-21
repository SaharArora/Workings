# GLEE Agent + Research System

Two agents sharing auditable economic-policy infrastructure:

- `leaderboard/`: production agent with strategic communication.
- `research/`: IBO versus EG-SPM experiments without strategic language.

The authoritative build specification is [`docs/BUILD_SPEC.md`](docs/BUILD_SPEC.md).

## Development

Requires Python 3.12 and `uv`.

```bash
uv sync --dev
uv run pytest
```

Copy `.env.example` to `.env` and set `GLEE_API_KEY` after the SDK credential interface
has been verified. Never commit `.env` or credentials.

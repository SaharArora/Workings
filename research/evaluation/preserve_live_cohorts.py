"""Build immutable per-game manifests for completed pre-fix live runs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EVALUATION = ROOT / "research" / "evaluation"
COHORT_DIR = EVALUATION / "cohorts"

COHORTS = {
    "PRE_RISK_FIX_BARGAINING_200": (
        "bargaining",
        (
            "leaderboard_live_bargaining_200_20260822.jsonl",
            "leaderboard_live_bargaining_200_20260822_part2.jsonl",
            "leaderboard_live_bargaining_200_20260822_part3.jsonl",
        ),
    ),
    "PRE_RISK_FIX_NEGOTIATION_INTERRUPT_4": (
        "negotiation",
        (
            "leaderboard_live_negotiation_200_20260822.jsonl",
            "leaderboard_live_negotiation_interrupted_drain_20260822.jsonl",
        ),
    ),
}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _events(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def preserve(cohort_id: str, family: str, names: tuple[str, ...]) -> None:
    source_paths = tuple(EVALUATION / name for name in names)
    games: dict[str, dict[str, Any]] = {}
    source_metadata: list[dict[str, Any]] = []
    all_timestamps: list[str] = []
    for path in source_paths:
        events = _events(path)
        timestamps = [str(item["timestamp"]) for item in events if item.get("timestamp")]
        all_timestamps.extend(timestamps)
        commits = sorted(
            {str(item["frozen_commit"]) for item in events if item.get("frozen_commit")}
        )
        source_metadata.append(
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": _hash(path),
                "start_time": min(timestamps) if timestamps else None,
                "end_time": max(timestamps) if timestamps else None,
                "frozen_commits": commits,
            }
        )
        for item in events:
            game_id: str | None = None
            if item.get("event") == "supervisor_event":
                supervisor = item.get("supervisor", {})
                if supervisor.get("event") == "game_tracked":
                    game_id = str(supervisor["game_id"])
            elif item.get("event") in {"policy_decision", "game_result"}:
                game_id = str(item["game_id"])
            if game_id is None:
                continue
            game = games.setdefault(
                game_id,
                {
                    "cohort_id": cohort_id,
                    "family": family,
                    "game_id": game_id,
                    "evidence_class": "OBSERVATIONAL_LIVE_EVIDENCE",
                    "randomized": False,
                    "experiment_assignment": None,
                    "source_logs": [],
                    "first_seen": None,
                    "terminal_time": None,
                    "frozen_commit": item.get("frozen_commit"),
                    "policy": None,
                    "terminal_outcome": None,
                    "raw_payoff": None,
                    "trace_status": "MISSING_TERMINAL_TRACE",
                },
            )
            relative = str(path.relative_to(ROOT))
            if relative not in game["source_logs"]:
                game["source_logs"].append(relative)
            timestamp = item.get("timestamp")
            if timestamp and (game["first_seen"] is None or timestamp < game["first_seen"]):
                game["first_seen"] = timestamp
            if item.get("event") == "policy_decision":
                game["policy"] = item.get("selected_policy") or item.get("routing", {}).get(
                    "selected_policy"
                )
            elif item.get("event") == "game_result":
                game.update(
                    {
                        "terminal_time": timestamp,
                        "policy": item.get("selected_policy") or game["policy"],
                        "terminal_outcome": item.get("outcome"),
                        "raw_payoff": item.get("raw_payoff"),
                        "trace_status": "COMPLETE_TERMINAL_TRACE",
                    }
                )

    ordered = [games[key] for key in sorted(games)]
    manifest_path = COHORT_DIR / f"{cohort_id}.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        "".join(json.dumps(item, sort_keys=True, default=str) + "\n" for item in ordered),
        encoding="utf-8",
    )
    policies = Counter(str(item["policy"]) for item in ordered)
    statuses = Counter(str(item["trace_status"]) for item in ordered)
    summary = {
        "cohort_id": cohort_id,
        "family": family,
        "evidence_class": "OBSERVATIONAL_LIVE_EVIDENCE",
        "randomized_game_count": 0,
        "experiment_assignments": {},
        "game_count": len(ordered),
        "start_time": min(all_timestamps) if all_timestamps else None,
        "end_time": max(all_timestamps) if all_timestamps else None,
        "frozen_commits": sorted(
            {
                str(item["frozen_commit"])
                for item in ordered
                if item.get("frozen_commit")
            }
        ),
        "policy_map": dict(sorted(policies.items())),
        "trace_status_counts": dict(sorted(statuses.items())),
        "source_logs": source_metadata,
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": _hash(manifest_path),
        "promotion_eprocess_eligible_games": 0,
        "reason": "NO_PRETREATMENT_RANDOMIZED_ASSIGNMENT",
    }
    (COHORT_DIR / f"{cohort_id}.summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    for cohort_id, (family, names) in COHORTS.items():
        preserve(cohort_id, family, names)


if __name__ == "__main__":
    main()


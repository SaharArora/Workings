"""Replay observable live decisions through the mechanical policy corrections."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from policies.negotiation.adaptive import adaptive_action_plan
from policies.persuasion.babbling import production_buyer_buys


def _records(paths: Iterable[Path]) -> Iterable[tuple[Path, dict[str, Any]]]:
    for path in sorted(paths):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield path, json.loads(line)


def _negotiation_replay(paths: Iterable[Path]) -> dict[str, Any]:
    decisions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    results: dict[str, dict[str, Any]] = {}
    sources: dict[str, set[str]] = defaultdict(set)
    for path, event in _records(paths):
        game_id = str(event.get("game_id", ""))
        if event.get("event") == "game_result" and game_id:
            results[game_id] = event
        if (
            event.get("event") != "policy_decision"
            or event.get("routing", {}).get("selected_policy")
            != "NEGOTIATION_ADAPTIVE"
        ):
            continue
        sources[game_id].add(path.name)
        old_action = dict(event["action"])
        game = {
            "game_id": game_id,
            "game_family": "negotiation",
            "your_player": event["state"].get("current_player"),
            "game_state": event["state"],
            "valid_actions": event["valid_actions"],
            "opponent": event.get("opponent", {}),
        }
        new_plan = adaptive_action_plan(game)
        new_action = dict(new_plan.action)
        old_counter = old_action.get("product_price")
        new_counter = new_action.get("product_price")
        opponent_offer = new_plan.observed_offer
        if old_counter is not None and new_counter is not None:
            toward = (
                float(new_counter) <= float(old_counter)
                if new_plan.role == "seller"
                else float(new_counter) >= float(old_counter)
            )
        elif new_action.get("decision") == "AcceptOffer":
            toward = True
        else:
            toward = None
        comparable_old = {
            key: old_action[key]
            for key in ("decision", "product_price")
            if key in old_action
        }
        comparable_new = {
            key: new_action[key]
            for key in ("decision", "product_price")
            if key in new_action
        }
        decisions[game_id].append(
            {
                "round": event["state"].get("round"),
                "role": new_plan.role,
                "opponent_offer": opponent_offer,
                "first_opponent_offer": new_plan.first_opponent_offer,
                "previous_best_offer": new_plan.previous_best_offer,
                "best_offer_seen": new_plan.best_offer_seen,
                "old_counter": old_counter,
                "new_counter": new_counter,
                "old_decision": old_action.get("decision"),
                "new_decision": new_action.get("decision"),
                "new_counter_moved_toward_agreement": toward,
                "strategic_action_changed": comparable_old != comparable_new,
            }
        )

    games = []
    for game_id in sorted(decisions):
        result = results.get(game_id, {})
        rows = decisions[game_id]
        changed = sum(bool(row["strategic_action_changed"]) for row in rows)
        games.append(
            {
                "game_id": game_id,
                "source_logs": sorted(sources[game_id]),
                "old_terminal_outcome": result.get("outcome", "UNOBSERVED"),
                "old_raw_payoff": result.get("raw_payoff"),
                "counterfactual_outcome_known": changed == 0
                and result.get("outcome") is not None,
                "counterfactual_outcome_note": (
                    "Historical outcome remains applicable because all strategic actions match."
                    if changed == 0 and result.get("outcome") is not None
                    else "Unknown: the transcript does not reveal the opponent response to changed actions."
                ),
                "decisions": rows,
            }
        )
    return {
        "games": games,
        "adaptive_games": len(games),
        "adaptive_decisions": sum(len(game["decisions"]) for game in games),
        "adaptive_decisions_changed": sum(
            bool(row["strategic_action_changed"])
            for game in games
            for row in game["decisions"]
        ),
    }


def _persuasion_replay(paths: Iterable[Path]) -> dict[str, Any]:
    games: dict[str, dict[str, Any]] = {}
    for path, event in _records(paths):
        if event.get("event") != "policy_decision":
            continue
        state = event.get("state", {})
        if event.get("valid_actions", {}).get("type") != "buyer_decision":
            continue
        required = ("p", "v", "u", "product_price")
        if any(key not in state for key in required):
            continue
        game_id = str(event["game_id"])
        expected_value = float(state["p"]) * float(state["v"]) + (
            1 - float(state["p"])
        ) * float(state["u"])
        old_decision = str(event["action"].get("decision"))
        new_decision = (
            "yes"
            if production_buyer_buys(expected_value, float(state["product_price"]))
            else "no"
        )
        game = games.setdefault(
            game_id,
            {
                "game_id": game_id,
                "source_logs": set(),
                "expected_value": expected_value,
                "product_price": float(state["product_price"]),
                "old_decision": old_decision,
                "new_decision": new_decision,
                "decision_count": 0,
                "flipped_decisions": 0,
            },
        )
        game["source_logs"].add(path.name)
        game["decision_count"] += 1
        game["flipped_decisions"] += old_decision != new_decision
    serialized = []
    for game_id in sorted(games):
        game = games[game_id]
        game["source_logs"] = sorted(game["source_logs"])
        serialized.append(game)
    return {
        "games": serialized,
        "buyer_games": len(serialized),
        "buyer_decisions": sum(game["decision_count"] for game in serialized),
        "buyer_decisions_flipped": sum(
            game["flipped_decisions"] for game in serialized
        ),
    }


def replay(evaluation_dir: Path) -> dict[str, Any]:
    negotiation_paths = evaluation_dir.glob("*negotiation*.jsonl")
    persuasion_paths = evaluation_dir.glob("*persuasion*.jsonl")
    return {
        "scope": "all repository live evaluation transcripts",
        "interpretation": {
            "observable": "policy actions are recomputed from the exact logged pre-action state",
            "counterfactual_limit": (
                "changed actions do not identify opponent responses or terminal payoff"
            ),
        },
        "negotiation_adaptive": _negotiation_replay(negotiation_paths),
        "persuasion_buyer_margin": _persuasion_replay(persuasion_paths),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evaluation_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = replay(args.evaluation_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

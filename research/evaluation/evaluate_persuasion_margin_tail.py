"""Historical tail-risk comparison for persuasion buyer indifference rules."""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from policies.persuasion.babbling import production_buyer_buys

TAIL_ALPHA = 0.90
MIN_PERCENTILE_GROUP_GAMES = 20


def _game_dirs(root: Path) -> Iterable[tuple[str, Path]]:
    for source in ("human_vs_llm", "llm_vs_llm"):
        for config in sorted((root / source / "persuasion").rglob("config.json")):
            if (config.parent / "game.csv").is_file():
                yield source, config.parent


def _tail_mean(values: list[float], *, alpha: float = TAIL_ALPHA) -> float:
    """Mean payoff over the worst ``1-alpha`` observations, fractional at boundary."""
    ordered = sorted(values)
    mass = (1.0 - alpha) * len(ordered)
    remaining = mass
    total = 0.0
    for value in ordered:
        used = min(1.0, remaining)
        total += used * value
        remaining -= used
        if remaining <= 1e-12:
            break
    return total / mass


def _group_candidates(args: dict[str, Any]) -> tuple[str, ...]:
    price = max(abs(float(args["product_price"])), 1.0)
    exact = "|".join(
        (
            str(args.get("seller_message_type", "unknown")),
            f"p={float(args['p']):.9g}",
            f"v={float(args['v']):.9g}",
            f"u={float(args.get('c', args.get('u', 0.0))):.9g}",
        )
    )
    broad = "|".join(
        (
            str(args.get("seller_message_type", "unknown")),
            f"p={float(args['p']):.9g}",
        )
    )
    return exact, broad, f"all|scale={math.floor(math.log10(price))}"


def _parse_game(source: str, directory: Path) -> dict[str, Any]:
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    args = config["game_args"]
    price = float(args["product_price"])
    high = float(args["v"]) * price
    low = float(args.get("c", args.get("u", 0.0))) * price
    expected = float(args["p"]) * high + (1.0 - float(args["p"])) * low
    theory_buy = expected + 1e-12 * max(1.0, abs(expected), abs(price)) >= price
    production_buy = production_buyer_buys(expected, price)
    qualities: dict[int, float] = {}
    decisions: dict[int, str] = {}
    with (directory / "game.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            round_number = int(float(row.get("round") or 0))
            worth = row.get("product_worth")
            if worth not in {None, ""}:
                qualities[round_number] = float(worth)
            decision = str(row.get("decision") or "").strip().lower()
            if decision in {"yes", "no"}:
                decisions[round_number] = decision
    rounds = sorted(qualities)
    actual = sum(
        qualities[round_number] - price
        for round_number in rounds
        if decisions.get(round_number) == "yes"
    )
    theory = sum(
        qualities[round_number] - price for round_number in rounds if theory_buy
    )
    production = sum(
        qualities[round_number] - price for round_number in rounds if production_buy
    )
    return {
        "game_id": directory.name,
        "source": source,
        "groups": _group_candidates(args),
        "price": price,
        "rounds": len(rounds),
        "expected_value": expected,
        "theory_buy": theory_buy,
        "production_buy": production_buy,
        "actual_payoff": actual,
        "theory_payoff": theory,
        "production_payoff": production,
        "theory_normalized": theory / (price * max(len(rounds), 1)),
        "production_normalized": production / (price * max(len(rounds), 1)),
    }


def _percentile(value: float, reference: list[float]) -> float:
    return bisect.bisect_right(reference, value) / len(reference)


def evaluate(root: Path) -> dict[str, Any]:
    games = [_parse_game(source, directory) for source, directory in _game_dirs(root)]
    references: dict[str, list[float]] = defaultdict(list)
    for game in games:
        for group in game["groups"]:
            references[group].append(float(game["actual_payoff"]))
    for values in references.values():
        values.sort()
    for game in games:
        game["percentile_group"] = next(
            group
            for group in game["groups"]
            if len(references[group]) >= MIN_PERCENTILE_GROUP_GAMES
        )
    policies: dict[str, Any] = {}
    for policy in ("theory", "production"):
        raw = [float(game[f"{policy}_payoff"]) for game in games]
        normalized = [float(game[f"{policy}_normalized"]) for game in games]
        percentiles = [
            _percentile(
                float(game[f"{policy}_payoff"]),
                references[str(game["percentile_group"])],
            )
            for game in games
        ]
        policies[policy] = {
            "games": len(games),
            "mean_raw_payoff": statistics.fmean(raw),
            "mean_normalized_payoff": statistics.fmean(normalized),
            "downside_frequency": sum(value < 0 for value in raw) / len(raw),
            "zero_payoff_frequency": sum(value == 0 for value in raw) / len(raw),
            "lower_tail_payoff_CVaR_0_90": _tail_mean(raw),
            "lower_tail_normalized_CVaR_0_90": _tail_mean(normalized),
            "mean_historical_percentile_proxy": statistics.fmean(percentiles),
        }
    changed = [game for game in games if game["theory_buy"] != game["production_buy"]]
    return {
        "source_commit": "68a33e98b035b97f945badee8f325001555c0049",
        "games": len(games),
        "theory_rule": "buy when EV>=price",
        "production_rule": "buy when EV>=1.02*price for price>0",
        "changed_rule_games": len(changed),
        "changed_rule_game_rate": len(changed) / len(games),
        "policies": policies,
        "rankings": {
            "raw_payoff": sorted(
                policies,
                key=lambda name: policies[name]["mean_raw_payoff"],
                reverse=True,
            ),
            "lower_tail_payoff": sorted(
                policies,
                key=lambda name: policies[name]["lower_tail_payoff_CVaR_0_90"],
                reverse=True,
            ),
            "percentile_proxy": sorted(
                policies,
                key=lambda name: policies[name]["mean_historical_percentile_proxy"],
                reverse=True,
            ),
        },
        "interpretation": (
            "Nature's realized product worth is observed. Rule payoffs are deterministic "
            "historical-state replays; they do not model strategic seller-message changes."
        ),
        "p3_redesigned": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.source_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

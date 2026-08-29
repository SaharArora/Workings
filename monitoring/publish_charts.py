#!/usr/bin/env python3
"""Publish sanitized, numeric-axis leaderboard charts from read-only exports."""

from __future__ import annotations

import argparse
import csv
import html
import math
import re
import shutil
import statistics
from pathlib import Path
from typing import Iterable, Mapping, Sequence


FAMILIES = ("bargaining", "negotiation", "persuasion")
THEORY = "#f59e0b"
EXPLOIT = "#2563eb"
EWMA = "#111827"
BLOCK = "#7c3aed"
ROLLING = "#059669"
GRID = "#dbe3ee"
AXIS = "#64748b"
TEXT = "#111827"
WIDTH, HEIGHT = 1120, 520
LEFT, RIGHT, TOP, BOTTOM = 92, 1090, 58, 420


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _write_if_changed(path: Path, text: str) -> bool:
    encoded = text.encode("utf-8")
    if path.is_file() and path.read_bytes() == encoded:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    return True


def _ewma(values: Sequence[float], span: int) -> list[float]:
    alpha = 2.0 / (span + 1.0)
    result: list[float] = []
    current: float | None = None
    for value in values:
        current = value if current is None else alpha * value + (1 - alpha) * current
        result.append(current)
    return result


def _rolling(values: Sequence[float], window: int) -> list[float | None]:
    result: list[float | None] = []
    for index in range(len(values)):
        start = max(0, index + 1 - window)
        result.append(
            statistics.fmean(values[start : index + 1])
            if index + 1 >= window
            else None
        )
    return result


def _polyline(points: Iterable[tuple[float, float]], color: str, width: float, dash: str = "") -> str:
    coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    if not coordinates:
        return ""
    dashed = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<polyline points="{coordinates}" fill="none" stroke="{color}" '
        f'stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"{dashed}/>'
    )


def _nice_ticks(low: float, high: float, target: int = 5) -> list[float]:
    if math.isclose(low, high):
        low -= 1.0
        high += 1.0
    padding = max((high - low) * 0.08, 1.0)
    low, high = low - padding, high + padding
    rough = (high - low) / max(target - 1, 1)
    magnitude = 10 ** math.floor(math.log10(rough))
    fraction = rough / magnitude
    nice = 1 if fraction <= 1 else 2 if fraction <= 2 else 5 if fraction <= 5 else 10
    step = nice * magnitude
    first = math.floor(low / step) * step
    last = math.ceil(high / step) * step
    count = int(round((last - first) / step))
    return [first + index * step for index in range(count + 1)]


def _x(number: int, count: int) -> float:
    return LEFT + (RIGHT - LEFT) * (number - 1) / max(1, count - 1)


def _x_ticks(count: int) -> list[int]:
    if count <= 1:
        return [1]
    rough = count / 6
    magnitude = 10 ** math.floor(math.log10(max(rough, 1)))
    fraction = rough / magnitude
    step = (1 if fraction <= 1 else 2 if fraction <= 2 else 5 if fraction <= 5 else 10) * magnitude
    ticks = list(range(0, count + 1, int(step)))
    if not ticks or ticks[0] != 1:
        ticks = [1, *[tick for tick in ticks if tick > 1]]
    if ticks[-1] != count:
        ticks.append(count)
    return sorted(set(ticks))


def _svg_start(title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="#fcfcfd"/>',
        f'<text x="24" y="31" font-family="system-ui,sans-serif" font-size="20" font-weight="700" fill="{TEXT}">{_escape(title)}</text>',
    ]


def _axes(
    count: int,
    y_ticks: Sequence[float],
    y_at,
    y_label: str,
    *,
    y_format,
    zero_line: bool = False,
) -> list[str]:
    output: list[str] = []
    for tick in y_ticks:
        y = y_at(tick)
        color = "#dc2626" if zero_line and math.isclose(tick, 0.0) else GRID
        width = 2.2 if zero_line and math.isclose(tick, 0.0) else 1
        dash = ' stroke-dasharray="7,5"' if zero_line and math.isclose(tick, 0.0) else ""
        output.append(f'<line x1="{LEFT}" y1="{y:.2f}" x2="{RIGHT}" y2="{y:.2f}" stroke="{color}" stroke-width="{width}"{dash}/>')
        output.append(f'<text x="{LEFT-10}" y="{y+4:.2f}" text-anchor="end" font-family="system-ui,sans-serif" font-size="12" fill="{color if zero_line and math.isclose(tick,0.0) else AXIS}">{_escape(y_format(tick))}</text>')
    for tick in _x_ticks(count):
        x = _x(tick, count)
        output.append(f'<line x1="{x:.2f}" y1="{BOTTOM}" x2="{x:.2f}" y2="{BOTTOM+5}" stroke="{AXIS}"/>')
        output.append(f'<text x="{x:.2f}" y="{BOTTOM+21}" text-anchor="middle" font-family="system-ui,sans-serif" font-size="11" fill="{AXIS}">{tick}</text>')
    output.extend(
        [
            f'<line x1="{LEFT}" y1="{TOP}" x2="{LEFT}" y2="{BOTTOM}" stroke="{AXIS}"/>',
            f'<line x1="{LEFT}" y1="{BOTTOM}" x2="{RIGHT}" y2="{BOTTOM}" stroke="{AXIS}"/>',
            f'<text x="{(LEFT+RIGHT)/2:.2f}" y="{HEIGHT-18}" text-anchor="middle" font-family="system-ui,sans-serif" font-size="13" fill="{AXIS}">Games played</text>',
            f'<text x="22" y="{(TOP+BOTTOM)/2:.2f}" text-anchor="middle" transform="rotate(-90 22 {(TOP+BOTTOM)/2:.2f})" font-family="system-ui,sans-serif" font-size="13" fill="{AXIS}">{_escape(y_label)}</text>',
        ]
    )
    return output


def _legend_item(x: int, color: str, label: str, *, line: bool = False, dash: str = "") -> str:
    if line:
        dashed = f' stroke-dasharray="{dash}"' if dash else ""
        sample = f'<line x1="{x}" y1="461" x2="{x+24}" y2="461" stroke="{color}" stroke-width="3"{dashed}/>'
    else:
        sample = f'<circle cx="{x+12}" cy="461" r="5" fill="{color}"/>'
    return sample + f'<text x="{x+31}" y="465" font-family="system-ui,sans-serif" font-size="11" fill="{TEXT}">{_escape(label)}</text>'


def _rating_svg(family: str, rows: Sequence[Mapping[str, str]]) -> str:
    observed = [(index, row) for index, row in enumerate(rows, start=1) if row.get("rating")]
    values = [float(row["rating"]) for _, row in observed]
    if not values:
        return "".join(_svg_start(f"{family.title()} authenticated leaderboard rating") + ["</svg>"])
    ticks = _nice_ticks(min(values), max(values))
    low, high = ticks[0], ticks[-1]
    y_at = lambda value: BOTTOM - (float(value) - low) * (BOTTOM - TOP) / max(high - low, 1e-9)
    output = _svg_start(f"{family.title()} authenticated leaderboard rating")
    output += _axes(len(rows), ticks, y_at, "Leaderboard rating", y_format=lambda value: f"{value:,.0f}")
    for index, row in observed:
        color = THEORY if row.get("arm") == "THEORY" else EXPLOIT
        output.append(
            f'<circle cx="{_x(index,len(rows)):.2f}" cy="{y_at(float(row["rating"])):.2f}" r="3.3" fill="{color}" opacity="0.82"><title>Game {index}: {row.get("arm","unknown")} · rating {float(row["rating"]):.2f}</title></circle>'
        )
    smooth = _ewma(values, 40)
    output.append(_polyline([(_x(index, len(rows)), y_at(value)) for (index, _), value in zip(observed, smooth)], EWMA, 3.2))
    output += [
        _legend_item(100, THEORY, "THEORY game"),
        _legend_item(245, EXPLOIT, "EXPLOIT game"),
        _legend_item(395, EWMA, "EWMA span 40", line=True),
        "</svg>",
    ]
    return "".join(output)


def _payoff_svg(family: str, rows: Sequence[Mapping[str, str]]) -> str:
    values = [max(0.0, min(1.0, float(row["normalized_own_payoff"]))) for row in rows]
    y_at = lambda value: BOTTOM - float(value) * (BOTTOM - TOP)
    ticks = (0.0, 0.25, 0.50, 0.75, 1.0)
    output = _svg_start(f"{family.title()} normalized own payoff")
    output += _axes(len(rows), ticks, y_at, "Normalized own payoff", y_format=lambda value: f"{value:.2f}", zero_line=True)
    output.append(f'<text x="{RIGHT-4}" y="{y_at(0)+16:.2f}" text-anchor="end" font-family="system-ui,sans-serif" font-size="11" font-weight="700" fill="#dc2626">zero payoff</text>')
    for index, (row, value) in enumerate(zip(rows, values), start=1):
        color = THEORY if row.get("arm") == "THEORY" else EXPLOIT
        output.append(
            f'<circle cx="{_x(index,len(rows)):.2f}" cy="{y_at(value):.2f}" r="2.5" fill="{color}" opacity="0.48"><title>Game {index}: {row.get("arm","unknown")} · payoff {value:.4f}</title></circle>'
        )
    blocks = [(end, statistics.fmean(values[end-10:end])) for end in range(10, len(values)+1, 10)]
    smooth = _ewma(values, 30)
    rolling = _rolling(values, 50)
    output.append(_polyline([(_x(end, len(rows)), y_at(value)) for end, value in blocks], BLOCK, 2.2))
    output.append(_polyline([(_x(index, len(rows)), y_at(value)) for index, value in enumerate(smooth, start=1)], EWMA, 3.2))
    output.append(_polyline([(_x(index, len(rows)), y_at(value)) for index, value in enumerate(rolling, start=1) if value is not None], ROLLING, 2.2, "7,5"))
    output += [
        _legend_item(100, THEORY, "THEORY game"),
        _legend_item(230, EXPLOIT, "EXPLOIT game"),
        _legend_item(370, BLOCK, "10-game block mean", line=True),
        _legend_item(555, EWMA, "EWMA span 30", line=True),
        _legend_item(710, ROLLING, "rolling 50", line=True, dash="7,5"),
        "</svg>",
    ]
    return "".join(output)


def _copy_if_changed(source: Path, destination: Path) -> bool:
    if destination.is_file() and destination.read_bytes() == source.read_bytes():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return True


def _publish_sanitized_svg(source: Path, destination: Path) -> bool:
    """Remove operational identities while preserving chart meaning and policy labels."""
    svg = source.read_text(encoding="utf-8")
    svg = re.sub(r"\s*·\s*(?:unit|raw config) [^·<]+", "", svg)
    svg = re.sub(
        r">([A-Z][A-Z0-9_]+)\s*·\s*[^<]+</text>",
        r">\1</text>",
        svg,
    )
    svg = svg.replace(
        "Lane label = Appendix A.1 class · evidence-unit prefix; hover a point for the full frozen identities and policy.",
        "Lane label = Appendix A.1 class; hover a point for the whole-game arm and policy.",
    )
    svg = re.sub(
        r" · [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=</title>)",
        "",
        svg,
    )
    return _write_if_changed(destination, svg)


def _readme(gangster: Sequence[Mapping[str, str]], yakuza: Sequence[Mapping[str, str]]) -> str:
    g_counts = {family: sum(row["family"] == family for row in gangster) for family in FAMILIES}
    y_counts = {family: sum(row["family"] == family for row in yakuza) for family in FAMILIES}
    g_latest = max((row["completed_at"] for row in gangster), default="not yet available")
    y_latest = max((row["completed_at"] for row in yakuza), default="not yet available")
    lines = [
        "# Leaderboard chart snapshots",
        "",
        "Read-only, sanitized chart snapshots. Credentials, assignment secrets, game IDs, raw game state, databases, and process locks are not published.",
        "",
        "Orange points are whole-game **THEORY** and blue points are whole-game **EXPLOIT**. Rating and payoff charts have numeric axes; payoff charts mark `0.00` explicitly. Public files are replaced on a 30-minute cadence when their source data changes.",
        "",
        "## GangsterYoshi Phase B V26",
        "",
        f"Latest completed game: `{g_latest}`. Charted V26 games (excluded canaries plus ordinary live volume): bargaining {g_counts['bargaining']}, negotiation {g_counts['negotiation']}, persuasion {g_counts['persuasion']}.",
        "",
        "The configuration-policy charts put games on the x-axis and the registered Appendix A.1 strategic configuration class on the y-axis. Point color shows the exact whole-game arm used. Bargaining and negotiation refill independently instead of waiting for the slower persuasion family.",
        "",
    ]
    for family in FAMILIES:
        title = family.title()
        lines += [
            f"- [{title} rating](gangsteryoshi-v26/{family}-rating.svg)",
            f"- [{title} payoff](gangsteryoshi-v26/{family}-payoff.svg)",
            f"- [{title} configuration and policy](gangsteryoshi-v26/{family}-configuration-policy.svg)",
        ]
    lines += [
        "",
        "## YakuzaYoshi Phase B V24 validation",
        "",
        f"Latest completed game: `{y_latest}`. Charted games (excluded canaries plus ordinary validation): bargaining {y_counts['bargaining']}, negotiation {y_counts['negotiation']}, persuasion {y_counts['persuasion']}.",
        "",
        "The configuration-policy charts put games on the x-axis and the registered Appendix A.1 strategic configuration unit on the y-axis. Point color shows the exact whole-game arm used.",
        "",
    ]
    for family in FAMILIES:
        title = family.title()
        lines += [
            f"- [{title} rating and policy](yakuzayoshi-v24/{family}-rating.svg)",
            f"- [{title} configuration and policy](yakuzayoshi-v24/{family}-configuration-policy.svg)",
        ]
    return "\n".join(lines) + "\n"


def _preserve_yakuza_readme(output_root: Path, gangster: Sequence[Mapping[str, str]]) -> str:
    current = output_root / "README.md"
    marker = "## YakuzaYoshi Phase B V24 validation"
    if not current.is_file():
        raise RuntimeError("gangster-only publication requires the existing sanitized Yakuza README section")
    previous = current.read_text(encoding="utf-8")
    if marker not in previous:
        raise RuntimeError("existing sanitized Yakuza README section is missing")
    preserved = marker + previous.split(marker, 1)[1]
    return _readme(gangster, []).split(marker, 1)[0] + preserved


def publish(gangster_root: Path, yakuza_root: Path | None, output_root: Path) -> int:
    gangster = _read_csv(gangster_root / "games.csv")
    yakuza = _read_csv(yakuza_root / "games.csv") if yakuza_root is not None else []
    changed = 0
    for family in FAMILIES:
        rows = [row for row in gangster if row["family"] == family]
        changed += _write_if_changed(output_root / "gangsteryoshi-v26" / f"{family}-rating.svg", _rating_svg(family, rows))
        changed += _write_if_changed(output_root / "gangsteryoshi-v26" / f"{family}-payoff.svg", _payoff_svg(family, rows))
        configuration = gangster_root / f"{family}-configuration-policy.svg"
        if configuration.is_file():
            changed += _publish_sanitized_svg(
                configuration,
                output_root / "gangsteryoshi-v26" / configuration.name,
            )
        if yakuza_root is not None:
            for suffix in ("rating.svg", "configuration-policy.svg"):
                source = yakuza_root / f"{family}-{suffix}"
                if source.is_file():
                    changed += _publish_sanitized_svg(
                        source, output_root / "yakuzayoshi-v24" / source.name
                    )
    readme = (
        _readme(gangster, yakuza)
        if yakuza_root is not None
        else _preserve_yakuza_readme(output_root, gangster)
    )
    changed += _write_if_changed(output_root / "README.md", readme)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gangster-root", type=Path, required=True)
    parser.add_argument(
        "--yakuza-root",
        type=Path,
        help="Optional stopped-campaign export; omit to preserve the existing sanitized V24 snapshot.",
    )
    parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    changed = publish(args.gangster_root, args.yakuza_root, args.output_root)
    print(f"published_changes={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

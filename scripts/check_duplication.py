"""
The copy-paste ratchet (docs/dev/code-health.md). jscpd reads .jscpd.json,
writes its JSON report and itself fails when the duplicated share of the
code rises above the config's `threshold`. This check then fails on a clone
of more than 20 lines that .jscpd-large-clones.json does not list, and on a
listed one that is gone, so the list only shrinks:

    npx --yes jscpd@5.4.0 --config .jscpd.json      # or `just duplication`
    uv run python -m scripts.check_duplication        # the check
    uv run python -m scripts.check_duplication --update   # rewrite the list

Rewrite the list only to remove clones that are gone, or after a review
agrees that a new large clone must stay; extract a shared helper otherwise.
Exit codes: 0 clean, 1 a new or a stale large clone, 2 an unreadable input.
"""

import argparse
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

LARGE_CLONE_LINES: int = 20
# Below the recorded threshold by this much, the threshold should come down.
THRESHOLD_SLACK_PERCENT: float = 0.05
DEFAULT_REPORT: Path = Path(".jscpd-report/jscpd-report.json")
DEFAULT_LARGE_CLONES: Path = Path(".jscpd-large-clones.json")
DEFAULT_CONFIG: Path = Path(".jscpd.json")
EXIT_OK: int = 0
EXIT_RATCHET: int = 1
EXIT_UNUSABLE: int = 2


@dataclass(frozen=True, order=True)
class ClonePair:
    """The two files one clone joins, in path order."""

    first_file: str
    second_file: str

    @classmethod
    def of(cls, one_file: str, other_file: str) -> ClonePair:
        first_file, second_file = sorted((one_file, other_file))
        return cls(first_file=first_file, second_file=second_file)


@dataclass(frozen=True)
class LargeClone:
    """A clone over the line limit, where it starts in each file."""

    pair: ClonePair
    lines: int
    locations: str


@dataclass(frozen=True)
class RatchetVerdict:
    """Large clones the list does not allow, and allowed ones that are gone."""

    new_clones: list[LargeClone]
    stale_pairs: list[ClonePair]

    @property
    def holds(self) -> bool:
        return not self.new_clones and not self.stale_pairs


def large_clones(report: dict[str, Any]) -> list[LargeClone]:
    clones: list[LargeClone] = []
    for duplicate in report["duplicates"]:
        lines: int = int(duplicate["lines"])
        if lines <= LARGE_CLONE_LINES:
            continue

        first: dict[str, Any] = duplicate["firstFile"]
        second: dict[str, Any] = duplicate["secondFile"]
        clones.append(
            LargeClone(
                pair=ClonePair.of(str(first["name"]), str(second["name"])),
                lines=lines,
                locations=(
                    f"{first['name']}:{first['start']} and "
                    f"{second['name']}:{second['start']}"
                ),
            )
        )
    return sorted(clones, key=lambda clone: (clone.pair, -clone.lines))


def count_by_pair(clones: list[LargeClone]) -> Counter[ClonePair]:
    return Counter(clone.pair for clone in clones)


def read_allowed_clones(document: dict[str, Any]) -> Counter[ClonePair]:
    allowed: Counter[ClonePair] = Counter()
    for entry in document["clones"]:
        one_file, other_file = entry["files"]
        allowed[ClonePair.of(str(one_file), str(other_file))] += int(entry["count"])
    return allowed


def allowed_clones_document(counts: Counter[ClonePair]) -> dict[str, Any]:
    return {
        "clones": [
            {"files": [pair.first_file, pair.second_file], "count": counts[pair]}
            for pair in sorted(counts)
        ]
    }


def compare(clones: list[LargeClone], allowed: Counter[ClonePair]) -> RatchetVerdict:
    current: Counter[ClonePair] = count_by_pair(clones)
    new_clones: list[LargeClone] = []
    for pair, count in current.items():
        if count > allowed[pair]:
            new_clones.extend(clone for clone in clones if clone.pair == pair)
    stale_pairs: list[ClonePair] = sorted(
        pair for pair, count in allowed.items() if current[pair] < count
    )
    return RatchetVerdict(new_clones=new_clones, stale_pairs=stale_pairs)


def threshold_notice(report: dict[str, Any], config: dict[str, Any]) -> str | None:
    """A reminder to lower the threshold once the share fell well below it."""

    percentage: float = float(report["statistics"]["total"]["percentage"])
    threshold: float = float(config["threshold"])
    if percentage > threshold - THRESHOLD_SLACK_PERCENT:
        return None

    lowered: float = math.ceil(percentage * 100) / 100
    return (
        f"Duplication is {percentage:.2f} %, the threshold {threshold:.2f} %: "
        f'lower "threshold" in .jscpd.json to {lowered:.2f}.'
    )


def describe(verdict: RatchetVerdict) -> str:
    lines: list[str] = []
    if verdict.new_clones:
        lines.append(
            f"New clones over {LARGE_CLONE_LINES} lines: extract the shared "
            "code into one helper (docs/dev/code-health.md)."
        )
        lines.extend(
            f"  {clone.lines} lines: {clone.locations}" for clone in verdict.new_clones
        )
    if verdict.stale_pairs:
        lines.append(
            "Gone from the code, still allowed: run "
            "`uv run python -m scripts.check_duplication --update`."
        )
        lines.extend(
            f"  {pair.first_file} and {pair.second_file}"
            for pair in verdict.stale_pairs
        )
    return "\n".join(lines)


def read_json(path: Path) -> dict[str, Any]:
    parsed: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} is not a JSON object")
    return cast(dict[str, Any], parsed)


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Fail on large clones .jscpd-large-clones.json does not list."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--allowed", type=Path, default=DEFAULT_LARGE_CLONES)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--update", action="store_true")
    options = parser.parse_args(arguments)
    try:
        report: dict[str, Any] = read_json(options.report)
        clones: list[LargeClone] = large_clones(report)
        if options.update:
            document = allowed_clones_document(count_by_pair(clones))
            options.allowed.write_text(
                json.dumps(document, indent=2) + "\n", encoding="utf-8"
            )
            print(f"{options.allowed}: {len(clones)} large clones listed.")
            return EXIT_OK

        allowed: Counter[ClonePair] = read_allowed_clones(read_json(options.allowed))
        notice: str | None = threshold_notice(report, read_json(options.config))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Cannot check the duplication: {error}", file=sys.stderr)
        return EXIT_UNUSABLE

    if notice is not None:
        print(notice)
    verdict: RatchetVerdict = compare(clones, allowed)
    if not verdict.holds:
        print(describe(verdict), file=sys.stderr)
        return EXIT_RATCHET

    print(f"{len(clones)} large clones, all listed in {options.allowed}.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

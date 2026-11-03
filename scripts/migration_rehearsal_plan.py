"""
The plan and the report of a migration rehearsal (scripts/migration_rehearsal.py):
which migrations production has already applied and which are pending, how
big the synthetic dataset is, and how long each pending migration took
against it, as JSON and as Markdown for the perf job's summary.

Pending migrations are the files of migrations/ that the commit production
runs (the `release` branch, render.yaml) does not have yet; without that
ref (a fresh clone, a fork) the newest `fallback_pending` files stand in.
Standard library only.
"""

import json
import subprocess  # nosec B404 - git, with fixed arguments
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

MIGRATION_SUFFIX: str = ".sql"
DEFAULT_FALLBACK_PENDING: int = 3
# One migration may hold the deploy this long against the full dataset;
# the deploy's lock timeout and retries are on top (migrations/README.md).
DEFAULT_BUDGET_SECONDS: float = 300.0


@dataclass(frozen=True)
class DatasetSize:
    """
    Rows the rehearsal writes per table, from the messages: production's
    shape in proportion (docs/operations/capacity.md: 2,000,000 messages,
    200,000 bookings for 500 businesses).
    """

    businesses: int
    messages: int

    @property
    def per_table(self) -> dict[str, int]:
        return {
            "contacts": self.messages // 10,
            "conversations": self.messages // 10,
            "messages": self.messages,
            "bookings": self.messages // 10,
            "inbound_events": self.messages // 2,
            "outbound_messages": self.messages // 4,
        }


SCALES: dict[str, DatasetSize] = {
    "full": DatasetSize(businesses=500, messages=2_000_000),
    "medium": DatasetSize(businesses=50, messages=200_000),
    "small": DatasetSize(businesses=10, messages=20_000),
}


@dataclass(frozen=True)
class RehearsalPlan:
    released: list[str]
    pending: list[str]
    base: str


@dataclass
class MigrationTiming:
    name: str
    seconds: float
    error: str | None = None


@dataclass
class RehearsalReport:
    base: str
    scale: str
    rows: dict[str, int]
    seed_seconds: float
    budget_seconds: float
    timings: list[MigrationTiming] = field(default_factory=list[MigrationTiming])

    @property
    def failures(self) -> list[str]:
        """Why the rehearsal fails: a migration that failed or ran too long."""

        return [
            f"{timing.name} failed: {timing.error}"
            if timing.error is not None
            else f"{timing.name} took {timing.seconds:.1f} s "
            f"(budget {self.budget_seconds:.0f} s)"
            for timing in self.timings
            if timing.error is not None or timing.seconds > self.budget_seconds
        ]

    def to_json(self) -> str:
        return json.dumps(asdict(self) | {"failures": self.failures}, indent=2) + "\n"

    def to_markdown(self) -> str:
        seeded: str = ", ".join(
            f"{count:,} {name}" for name, count in self.rows.items()
        )
        lines: list[str] = [
            f"### Migration rehearsal ({self.scale}, against {self.base})",
            "",
            f"Seeded in {self.seed_seconds:.1f} s: {seeded}.",
            "",
        ]
        if not self.timings:
            lines.append("No pending migration: production has every file.")
            return "\n".join(lines) + "\n"

        lines.extend(["| Migration | Seconds | |", "| --- | --- | --- |"])
        for timing in self.timings:
            verdict: str = (
                "**failed**"
                if timing.error is not None
                else "**over budget**"
                if timing.seconds > self.budget_seconds
                else "ok"
            )
            lines.append(f"| {timing.name} | {timing.seconds:.2f} | {verdict} |")

        return "\n".join(lines) + "\n"


def migration_names(directory: Path) -> list[str]:
    return sorted(path.stem for path in directory.glob(f"*{MIGRATION_SUFFIX}"))


def names_at_ref(ref: str, directory: str = "migrations") -> list[str] | None:
    """The migration names the commit `ref` has; None when git cannot read it."""

    completed = subprocess.run(  # nosec B603 B607 - fixed git arguments
        ["git", "ls-tree", "--name-only", f"{ref}:{directory}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None

    return sorted(
        Path(line).stem
        for line in completed.stdout.splitlines()
        if line.endswith(MIGRATION_SUFFIX)
    )


def plan_rehearsal(
    names: Sequence[str],
    released: Sequence[str] | None,
    base: str,
    fallback_pending: int = DEFAULT_FALLBACK_PENDING,
) -> RehearsalPlan:
    """
    Split the migrations into those production has and those it will run.
    A released name missing here (renamed or removed) is ignored; without
    the released list the newest `fallback_pending` files are pending.
    """

    ordered: list[str] = sorted(names)
    if released is None:
        cut: int = max(0, len(ordered) - fallback_pending)
        return RehearsalPlan(
            released=ordered[:cut],
            pending=ordered[cut:],
            base=f"the newest {len(ordered) - cut} file(s)",
        )

    known: set[str] = set(released)
    return RehearsalPlan(
        released=[name for name in ordered if name in known],
        pending=[name for name in ordered if name not in known],
        base=base,
    )

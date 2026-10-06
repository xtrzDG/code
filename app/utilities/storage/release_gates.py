"""
Release gates: stored enum values one release ahead.

During a deploy the previous release reads what the new one writes (and
after a rollback the other way round), and an enum value it does not know
fails the whole document. So a new value is added in two releases:

1. the release that adds it reads it and lists it here behind a CLOSED
   gate; storage refuses to write a value of a closed gate
   (`PersistedDocumentCodec`), so nothing writes it yet;
2. the next release opens the gate (`is_open=True`): the release before it
   knows the value now. Once that release is the previous one too, the
   gate goes.

`tests/architecture_policy/test_enum_values_are_known_one_release_ahead.py`
compares the enum values of every stored document with the snapshot of
the last release and fails on a new value that no closed gate covers.
Writers that choose between an old and a new value ask `is_gate_open`.
"""

import re
from collections.abc import Iterator, Sequence
from typing import cast

from app.schemas.dto.release_gates import ReleaseGate
from app.schemas.exceptions.storage_errors import ClosedReleaseGateError
from app.schemas.typings.maintenance.booleans import IsReleaseGateOpen
from app.schemas.typings.maintenance.constrained_strings import (
    GatedEnumValue,
    ReleaseGateName,
    StoredEnumPath,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName

SUBSCRIPTION_PAUSE_GATE: ReleaseGateName = ReleaseGateName("subscription_pause")

RELEASE_GATES: tuple[ReleaseGate, ...] = (
    # The seasonal pause (R14, migration 1161) stores a subscription as
    # `paused`; it opens in the next release. Pausing also needs
    # SUBSCRIPTION_PAUSE_ENABLED.
    ReleaseGate(
        name=SUBSCRIPTION_PAUSE_GATE,
        collection_name=DocumentCollectionName("subscriptions"),
        path=StoredEnumPath("status"),
        values=[GatedEnumValue("paused")],
        is_open=False,
    ),
)

PATH_STEP: re.Pattern[str] = re.compile(r"[a-z_][a-z0-9_]*|\[\]|\{\}")
LIST_STEP: str = "[]"
MAP_STEP: str = "{}"

type ClosedGate = tuple[tuple[str, ...], frozenset[str]]


def is_gate_open(
    name: ReleaseGateName, gates: Sequence[ReleaseGate] | None = None
) -> IsReleaseGateOpen:
    """
    Whether the gate lets the code write its values (an unknown name: no);
    `gates` default to this release's `RELEASE_GATES`.
    """

    return any(gate.name == name and gate.is_open for gate in gates_or_release(gates))


def path_steps(path: StoredEnumPath) -> tuple[str, ...]:
    """`results[].kind` -> ("results", "[]", "kind")."""

    return tuple(PATH_STEP.findall(str(path)))


def closed_gates_of(
    collection_name: DocumentCollectionName | None,
    gates: Sequence[ReleaseGate] | None = None,
) -> tuple[ClosedGate, ...]:
    """The closed gates of a collection, ready for `refuse_closed_values`."""

    return tuple(
        (path_steps(gate.path), frozenset(str(value) for value in gate.values))
        for gate in gates_or_release(gates)
        if not gate.is_open and gate.collection_name == collection_name
    )


def gates_or_release(gates: Sequence[ReleaseGate] | None) -> Sequence[ReleaseGate]:
    """
    The gates given, else this release's, read when asked (not when the
    caller was defined), so a test can stand in the next release.
    """

    return RELEASE_GATES if gates is None else gates


def values_at(node: object, steps: tuple[str, ...]) -> Iterator[object]:
    """Every value the path reaches in a JSON document (none when absent)."""

    if not steps:
        yield node
        return

    step, rest = steps[0], steps[1:]
    if step == LIST_STEP:
        if isinstance(node, list):
            for item in cast(list[object], node):
                yield from values_at(item, rest)
    elif step == MAP_STEP:
        if isinstance(node, dict):
            for item in cast(dict[str, object], node).values():
                yield from values_at(item, rest)
    elif isinstance(node, dict) and step in node:
        yield from values_at(cast(dict[str, object], node)[step], rest)


def refuse_closed_values(document: object, closed_gates: Sequence[ClosedGate]) -> None:
    """
    Raises:
        ClosedReleaseGateError: the document holds a value of a closed gate.
    """

    for steps, values in closed_gates:
        for value in values_at(document, steps):
            if isinstance(value, str) and value in values:
                raise ClosedReleaseGateError(
                    f"'{value}' at {'.'.join(steps)} is behind a closed release "
                    "gate: the previous release cannot read it yet."
                )

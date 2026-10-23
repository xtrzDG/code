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
OFFER_CHOICES_GATE: ReleaseGateName = ReleaseGateName("offer_choices_tool")
BOOKING_DEPOSITS_GATE: ReleaseGateName = ReleaseGateName("booking_deposits")
PAYMENT_LINK_TOOL_GATE: ReleaseGateName = ReleaseGateName("send_payment_link_tool")
OPS_LANE_GATE: ReleaseGateName = ReleaseGateName("ops_lane")
PROTECT_DATA_STEP_GATE: ReleaseGateName = ReleaseGateName("protect_data_step")
DECLINE_RECORDING_GATE: ReleaseGateName = ReleaseGateName("decline_recording_tool")
STRIPE_PAYMENTS_GATE: ReleaseGateName = ReleaseGateName("stripe_payments")
PHONE_NUMBER_RENTAL_GATE: ReleaseGateName = ReleaseGateName("phone_number_rental")
COMMENT_REPLIES_GATE: ReleaseGateName = ReleaseGateName("instagram_comment_replies")

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
    # The model tool offer_choices (R14): offered by every chat conversation
    # but never written as a version's tool or a stored tool call until the
    # next release opens these gates (the reply keeps the choices it made).
    ReleaseGate(
        name=OFFER_CHOICES_GATE,
        collection_name=DocumentCollectionName("assistant_versions"),
        path=StoredEnumPath("tools[]"),
        values=[GatedEnumValue("offer_choices")],
        is_open=False,
    ),
    ReleaseGate(
        name=OFFER_CHOICES_GATE,
        collection_name=DocumentCollectionName("messages"),
        path=StoredEnumPath("tool_calls[].tool_name"),
        values=[GatedEnumValue("offer_choices")],
        is_open=False,
    ),
    # Deposits (W19, migration 1190): a booking that waits for its deposit
    # is PENDING (with its deposit AWAITING) until the next release opens
    # this gate and writes PENDING_DEPOSIT.
    ReleaseGate(
        name=BOOKING_DEPOSITS_GATE,
        collection_name=DocumentCollectionName("bookings"),
        path=StoredEnumPath("status"),
        values=[GatedEnumValue("pending_deposit")],
        is_open=False,
    ),
    ReleaseGate(
        name=BOOKING_DEPOSITS_GATE,
        collection_name=DocumentCollectionName("bookings"),
        path=StoredEnumPath("last_status_change.previous_status"),
        values=[GatedEnumValue("pending_deposit")],
        is_open=False,
    ),
    # The model tool send_payment_link (W19): offered by the chat
    # conversations, never written as a version's tool or a stored tool
    # call until the next release opens these gates (the reply keeps the
    # payment line it carried).
    ReleaseGate(
        name=PAYMENT_LINK_TOOL_GATE,
        collection_name=DocumentCollectionName("assistant_versions"),
        path=StoredEnumPath("tools[]"),
        values=[GatedEnumValue("send_payment_link")],
        is_open=False,
    ),
    ReleaseGate(
        name=PAYMENT_LINK_TOOL_GATE,
        collection_name=DocumentCollectionName("messages"),
        path=StoredEnumPath("tool_calls[].tool_name"),
        values=[GatedEnumValue("send_payment_link")],
        is_open=False,
    ),
    # The platform alerts' own worker lane (W20): this release reads the
    # lane `ops` and runs its thread; the alerts are queued in it once the
    # next release opens this gate (until then they use the outbound lane,
    # where each provider holds at most half of the threads).
    ReleaseGate(
        name=OPS_LANE_GATE,
        collection_name=DocumentCollectionName("queued_jobs"),
        path=StoredEnumPath("lane"),
        values=[GatedEnumValue("ops")],
        is_open=False,
    ),
    # The setup guide's step "Protect your customers' data" (W20): an owner
    # puts it away with the second-factor reminder (security_nudges), so
    # it is never stored as a skipped step; the gate stays closed until a
    # release lets owners skip it like the other steps after the launch.
    ReleaseGate(
        name=PROTECT_DATA_STEP_GATE,
        collection_name=DocumentCollectionName("setup_states"),
        path=StoredEnumPath("skipped_steps[]"),
        values=[GatedEnumValue("protect_data")],
        is_open=False,
    ),
    ReleaseGate(
        name=PROTECT_DATA_STEP_GATE,
        collection_name=DocumentCollectionName("setup_states"),
        path=StoredEnumPath("skipped_after_launch[]"),
        values=[GatedEnumValue("protect_data")],
        is_open=False,
    ),
    # The phone tool decline_recording (W20): offered by every call's
    # conversation, never written as a version's tool or a stored tool call
    # until the next release opens these gates (the post-call report names
    # the call that declined its recording).
    ReleaseGate(
        name=DECLINE_RECORDING_GATE,
        collection_name=DocumentCollectionName("assistant_versions"),
        path=StoredEnumPath("tools[]"),
        values=[GatedEnumValue("decline_recording")],
        is_open=False,
    ),
    ReleaseGate(
        name=DECLINE_RECORDING_GATE,
        collection_name=DocumentCollectionName("messages"),
        path=StoredEnumPath("tool_calls[].tool_name"),
        values=[GatedEnumValue("decline_recording")],
        is_open=False,
    ),
    # Stripe (R17-PAYMENTS-REGIONAL, migration 1214): the provider registry
    # routes owners in the EU, the US and Israel to Stripe only once the
    # next release opens this gate; until then everyone pays through Flitt.
    *(
        ReleaseGate(
            name=STRIPE_PAYMENTS_GATE,
            collection_name=DocumentCollectionName(collection),
            path=StoredEnumPath(path),
            values=[GatedEnumValue("stripe")],
            is_open=False,
        )
        for collection, path in (
            ("payment_orders", "provider"),
            ("subscriptions", "payment_provider"),
            ("subscriptions", "payment_method_summary.provider"),
            ("payment_retry_attempts", "provider"),
        )
    ),
    # Rented phone numbers (W21, migration 1213): a rental month is a usage
    # event and an invoice of the kind `number_rental`; the rental job bills
    # no month until the next release opens these gates, then catches up
    # from each number's `billed_until`.
    ReleaseGate(
        name=PHONE_NUMBER_RENTAL_GATE,
        collection_name=DocumentCollectionName("usage_events"),
        path=StoredEnumPath("kind"),
        values=[GatedEnumValue("number_rental")],
        is_open=False,
    ),
    ReleaseGate(
        name=PHONE_NUMBER_RENTAL_GATE,
        collection_name=DocumentCollectionName("invoices"),
        path=StoredEnumPath("kind"),
        values=[GatedEnumValue("number_rental")],
        is_open=False,
    ),
    # Instagram comment-to-DM (W21, migration 1212): a comment that names one
    # of the owner's keywords is an inbox event COMMENT_TRIGGER and its
    # private reply an outbox message COMMENT_REPLY. Until the next release
    # opens this gate, comments are read and left alone (nothing stored).
    ReleaseGate(
        name=COMMENT_REPLIES_GATE,
        collection_name=DocumentCollectionName("inbound_events"),
        path=StoredEnumPath("kind"),
        values=[GatedEnumValue("comment_trigger")],
        is_open=False,
    ),
    ReleaseGate(
        name=COMMENT_REPLIES_GATE,
        collection_name=DocumentCollectionName("outbound_messages"),
        path=StoredEnumPath("kind"),
        values=[GatedEnumValue("comment_reply")],
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

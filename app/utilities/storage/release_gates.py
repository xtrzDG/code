"""
Release gates: stored enum values one release ahead.

During a deploy the previous release reads what the new one writes (and
after a rollback the other way round), and an enum value it does not know
fails the whole document. So a new value is added in two releases:

1. the release that adds it reads it and lists it behind a CLOSED gate:
   storage (`PersistedDocumentCodec`) refuses to write the value yet;
2. the next release opens the gate (`is_open=True`), as the release
   before it knows the value; once that one is gone too, the gate goes.

`tests/architecture_policy/test_enum_values_are_known_one_release_ahead.py`
compares the enum values of every stored document with the snapshot of
the last release and fails on a new value that no closed gate covers.
Writers that choose between an old and a new value ask `is_gate_open`.

Every gate below is open: the release before this one (launch-2026-11-05)
reads all their values, and the release after this one deletes them.
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
from app.utilities.storage.appended_release_gates import APPENDED_RELEASE_GATES

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
CALLBACK_REQUESTED_GATE: ReleaseGateName = ReleaseGateName("missed_call_callback")

RELEASE_GATES: tuple[ReleaseGate, ...] = (
    # Open from this release: the seasonal pause (R14, migration 1161) stores
    # `paused` once SUBSCRIPTION_PAUSE_ENABLED (off by default) is set.
    ReleaseGate(
        name=SUBSCRIPTION_PAUSE_GATE,
        collection_name=DocumentCollectionName("subscriptions"),
        path=StoredEnumPath("status"),
        values=[GatedEnumValue("paused")],
        is_open=True,
    ),
    # Open from this release: the chat tool offer_choices (R14) is kept in a
    # stored message (its result backs no reply, `reply_evidence`); a version
    # never lists it (conversation tools are no version's).
    ReleaseGate(
        name=OFFER_CHOICES_GATE,
        collection_name=DocumentCollectionName("assistant_versions"),
        path=StoredEnumPath("tools[]"),
        values=[GatedEnumValue("offer_choices")],
        is_open=True,
    ),
    ReleaseGate(
        name=OFFER_CHOICES_GATE,
        collection_name=DocumentCollectionName("messages"),
        path=StoredEnumPath("tool_calls[].tool_name"),
        values=[GatedEnumValue("offer_choices")],
        is_open=True,
    ),
    # Open from this release: a booking that waits for its deposit (W19,
    # migration 1190) is PENDING_DEPOSIT (deposits need the owner's settings).
    ReleaseGate(
        name=BOOKING_DEPOSITS_GATE,
        collection_name=DocumentCollectionName("bookings"),
        path=StoredEnumPath("status"),
        values=[GatedEnumValue("pending_deposit")],
        is_open=True,
    ),
    ReleaseGate(
        name=BOOKING_DEPOSITS_GATE,
        collection_name=DocumentCollectionName("bookings"),
        path=StoredEnumPath("last_status_change.previous_status"),
        values=[GatedEnumValue("pending_deposit")],
        is_open=True,
    ),
    # Open from this release: a stored message keeps the chat tool
    # send_payment_link (W19, needs deposit settings); no version lists it.
    ReleaseGate(
        name=PAYMENT_LINK_TOOL_GATE,
        collection_name=DocumentCollectionName("assistant_versions"),
        path=StoredEnumPath("tools[]"),
        values=[GatedEnumValue("send_payment_link")],
        is_open=True,
    ),
    ReleaseGate(
        name=PAYMENT_LINK_TOOL_GATE,
        collection_name=DocumentCollectionName("messages"),
        path=StoredEnumPath("tool_calls[].tool_name"),
        values=[GatedEnumValue("send_payment_link")],
        is_open=True,
    ),
    # Open from this release: the platform alerts, the critical-clients digest
    # and spend-limit notices queue in `ops` (W20), which production's customer
    # worker must name in WORKER_LANES before this release deploys (render.yaml;
    # docs/operations/deploys.md).
    ReleaseGate(
        name=OPS_LANE_GATE,
        collection_name=DocumentCollectionName("queued_jobs"),
        path=StoredEnumPath("lane"),
        values=[GatedEnumValue("ops")],
        is_open=True,
    ),
    # Open from this release: the setup step "Protect your customers' data"
    # (W20) may be stored, but nothing writes it yet (put away with the
    # second-factor reminder, and not in SKIPPABLE_STEPS).
    ReleaseGate(
        name=PROTECT_DATA_STEP_GATE,
        collection_name=DocumentCollectionName("setup_states"),
        path=StoredEnumPath("skipped_steps[]"),
        values=[GatedEnumValue("protect_data")],
        is_open=True,
    ),
    ReleaseGate(
        name=PROTECT_DATA_STEP_GATE,
        collection_name=DocumentCollectionName("setup_states"),
        path=StoredEnumPath("skipped_after_launch[]"),
        values=[GatedEnumValue("protect_data")],
        is_open=True,
    ),
    # Open from this release: a voice tool call's message keeps the phone tool
    # decline_recording (W20); no version lists it (calls need a phone line).
    ReleaseGate(
        name=DECLINE_RECORDING_GATE,
        collection_name=DocumentCollectionName("assistant_versions"),
        path=StoredEnumPath("tools[]"),
        values=[GatedEnumValue("decline_recording")],
        is_open=True,
    ),
    ReleaseGate(
        name=DECLINE_RECORDING_GATE,
        collection_name=DocumentCollectionName("messages"),
        path=StoredEnumPath("tool_calls[].tool_name"),
        values=[GatedEnumValue("decline_recording")],
        is_open=True,
    ),
    # Open from this release (R17-PAYMENTS-REGIONAL, migration 1214): owners in
    # the EU, the US and Israel pay through Stripe whenever STRIPE_SECRET_KEY and
    # its webhook secret are set. Deploy only once the account can charge and
    # 2026-11-22 has come (docs/LAUNCH.md, 4.7.2).
    *(
        ReleaseGate(
            name=STRIPE_PAYMENTS_GATE,
            collection_name=DocumentCollectionName(collection),
            path=StoredEnumPath(path),
            values=[GatedEnumValue("stripe")],
            is_open=True,
        )
        for collection, path in (
            ("payment_orders", "provider"),
            ("subscriptions", "payment_provider"),
            ("subscriptions", "payment_method_summary.provider"),
            ("payment_retry_attempts", "provider"),
        )
    ),
    # Open from this release: the rental job bills each month of a rented
    # number (W21, migration 1213; usage event, invoice `number_rental`) from its
    # `billed_until`. Numbers need PHONE_NUMBER_PROVIDER=twilio and its keys.
    ReleaseGate(
        name=PHONE_NUMBER_RENTAL_GATE,
        collection_name=DocumentCollectionName("usage_events"),
        path=StoredEnumPath("kind"),
        values=[GatedEnumValue("number_rental")],
        is_open=True,
    ),
    ReleaseGate(
        name=PHONE_NUMBER_RENTAL_GATE,
        collection_name=DocumentCollectionName("invoices"),
        path=StoredEnumPath("kind"),
        values=[GatedEnumValue("number_rental")],
        is_open=True,
    ),
    # Open from this release: Instagram comment-to-DM (W21, migration 1212). A
    # keyword comment is an inbox event COMMENT_TRIGGER, its private reply an
    # outbox COMMENT_REPLY; it needs the Meta keys, the `comments` webhook field
    # and instagram_manage_comments.
    ReleaseGate(
        name=COMMENT_REPLIES_GATE,
        collection_name=DocumentCollectionName("inbound_events"),
        path=StoredEnumPath("kind"),
        values=[GatedEnumValue("comment_trigger")],
        is_open=True,
    ),
    ReleaseGate(
        name=COMMENT_REPLIES_GATE,
        collection_name=DocumentCollectionName("outbound_messages"),
        path=StoredEnumPath("kind"),
        values=[GatedEnumValue("comment_reply")],
        is_open=True,
    ),
    # Open from this release: a call that asked for a callback and left staff
    # nothing (R16) is a missed call CALLBACK_REQUESTED (calls need a phone line).
    ReleaseGate(
        name=CALLBACK_REQUESTED_GATE,
        collection_name=DocumentCollectionName("missed_calls"),
        path=StoredEnumPath("reason"),
        values=[GatedEnumValue("callback_requested")],
        is_open=True,
    ),
    *APPENDED_RELEASE_GATES,  # Status payments (REL-06), send_call_transcript.
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

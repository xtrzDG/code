"""The usage a call meters: voice minutes and minutes after a transfer."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.voice_webhooks import FinishedCallReport
from app.schemas.typings.billing.constrained_integers import CostMicroUsd, UsageQuantity


def build_transfer_usage_event(
    call: CallDocument,
    report: FinishedCallReport,
    now: Microseconds,
) -> UsageEventDocument | None:
    """
    Minutes after the caller was put through to staff (concept
    `transfer_min`): from the transfer to the end of the call.
    """

    if report.transfer_offset_seconds is None:
        return None

    return UsageEventDocument(
        business_id=call.business_id,
        conversation_id=call.conversation_id,
        kind=UsageKind.TRANSFER_SECONDS,
        quantity=UsageQuantity(
            max(
                int(call.duration_seconds) - int(report.transfer_offset_seconds),
                0,
            )
        ),
        cost_micro_usd=CostMicroUsd(0),
        occurred_at=call.started_at,
        created_at=now,
        updated_at=now,
    )


def build_voice_usage_event(
    call: CallDocument, now: Microseconds
) -> UsageEventDocument:
    """The call's minutes, metered against the package."""

    return UsageEventDocument(
        business_id=call.business_id,
        conversation_id=call.conversation_id,
        kind=UsageKind.VOICE_SECONDS,
        quantity=UsageQuantity(int(call.duration_seconds)),
        cost_micro_usd=call.cost_micro_usd,
        occurred_at=call.started_at,
        created_at=now,
        updated_at=now,
    )

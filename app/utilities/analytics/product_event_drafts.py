"""
The product events of each step, built from the records the step has at
hand, so every use case reports its step in one line.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import ProductEventName, TunnelStepKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.setup import (
    ActivationEventKind,
    ApplyChangesStage,
    SetupStepCode,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.product_events import ProductEventProperties
from app.schemas.domain.setup import ApplyAttentionReason
from app.schemas.domain.users import UserDocument
from app.schemas.dto.analytics.product_event_drafts import ProductEventDraft
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.users.prefixed_id import UserId

# The skippable steps of the API's guided setup, as the tunnel names them.
SKIPPED_TUNNEL_STEPS: dict[SetupStepCode, TunnelStepKey] = {
    SetupStepCode.OFFER: TunnelStepKey.OFFER,
    SetupStepCode.CHANNELS: TunnelStepKey.CHANNELS,
    SetupStepCode.TEST: TunnelStepKey.TRY,
}
MILESTONE_EVENTS: dict[ActivationEventKind, ProductEventName] = {
    ActivationEventKind.TEST_CHAT_TRIED: ProductEventName.TEST_CHAT_TRIED,
    ActivationEventKind.WENT_LIVE: ProductEventName.WENT_LIVE,
    ActivationEventKind.FIRST_CONVERSATION: ProductEventName.FIRST_REAL_CONVERSATION,
    ActivationEventKind.FIRST_BOOKING: ProductEventName.FIRST_BOOKING,
    ActivationEventKind.FIRST_HANDOFF: ProductEventName.FIRST_HANDOFF,
}
LAUNCH_RESULTS: dict[ApplyChangesStage, ProductEventName] = {
    ApplyChangesStage.LIVE: ProductEventName.LAUNCH_SUCCEEDED,
    ApplyChangesStage.NEEDS_ATTENTION: ProductEventName.LAUNCH_BLOCKED,
}
# Channels a customer can reach the assistant in (not the owner's test).
CUSTOMER_CHANNELS: frozenset[ChannelKind] = frozenset(ChannelKind) - {
    ChannelKind.OWNER_TEST
}


def sign_in_events(
    user: UserDocument, is_new_user: bool
) -> tuple[ProductEventDraft, ...]:
    """A sign-in, preceded by the sign-up when the account is new."""

    facts = ProductEventProperties(login_method=user.login_method)
    sign_in = ProductEventDraft(
        name=ProductEventName.SIGNED_IN, user_id=user.id, properties=facts
    )
    if not is_new_user:
        return (sign_in,)

    sign_up = ProductEventDraft(
        name=ProductEventName.SIGNED_UP, user_id=user.id, properties=facts
    )
    return (sign_up, sign_in)


def business_created_event(
    business: BusinessDocument, owner_id: UserId
) -> ProductEventDraft:
    return ProductEventDraft(
        name=ProductEventName.BUSINESS_CREATED,
        user_id=owner_id,
        business_id=business.id,
        occurred_at=business.created_at,
    )


def tunnel_step_skipped_events(
    user_id: UserId,
    business_id: BusinessId,
    step: SetupStepCode,
    is_skipped: bool,
) -> tuple[ProductEventDraft, ...]:
    """
    The tunnel's step the owner skipped; none when they brought it back or
    for a step the tunnel never skips.
    """

    tunnel_step: TunnelStepKey | None = SKIPPED_TUNNEL_STEPS.get(step)
    if tunnel_step is None or not is_skipped:
        return ()

    return (
        ProductEventDraft(
            name=ProductEventName.TUNNEL_STEP_SKIPPED,
            user_id=user_id,
            business_id=business_id,
            properties=ProductEventProperties(tunnel_step=tunnel_step),
        ),
    )


def launch_result_events(
    business_id: BusinessId,
    stage: ApplyChangesStage,
    attention: Sequence[ApplyAttentionReason] = (),
) -> tuple[ProductEventDraft, ...]:
    """An apply that ended live or stopped for the owner; none on the way."""

    name: ProductEventName | None = LAUNCH_RESULTS.get(stage)
    if name is None:
        return ()

    codes = list(dict.fromkeys(reason.code for reason in attention))
    return (
        ProductEventDraft(
            name=name,
            business_id=business_id,
            properties=ProductEventProperties(attention_codes=codes),
        ),
    )


def launch_blocked_events(
    business_id: BusinessId, attention: Sequence[ApplyAttentionReason]
) -> tuple[ProductEventDraft, ...]:
    """An apply stopped for the owner's attention; none without a reason."""

    if not attention:
        return ()

    return launch_result_events(
        business_id, ApplyChangesStage.NEEDS_ATTENTION, attention
    )


def dpa_accepted_event(
    user_id: UserId, business_id: BusinessId, version: DpaDocumentVersion
) -> ProductEventDraft:
    return ProductEventDraft(
        name=ProductEventName.DPA_ACCEPTED,
        user_id=user_id,
        business_id=business_id,
        properties=ProductEventProperties(dpa_version=version),
    )


def channel_connected_events(
    user_id: UserId | None,
    business_id: BusinessId,
    channel: ChannelKind,
    occurred_at: Microseconds | None = None,
) -> tuple[ProductEventDraft, ...]:
    """A channel customers can write in was connected (once per kind)."""

    if channel not in CUSTOMER_CHANNELS:
        return ()

    return (
        ProductEventDraft(
            name=ProductEventName.CHANNEL_CONNECTED,
            user_id=user_id,
            business_id=business_id,
            properties=ProductEventProperties(channel=channel),
            occurred_at=occurred_at,
        ),
    )


def milestone_event(
    business_id: BusinessId, kind: ActivationEventKind, occurred_at: Microseconds
) -> ProductEventDraft:
    return ProductEventDraft(
        name=MILESTONE_EVENTS[kind], business_id=business_id, occurred_at=occurred_at
    )

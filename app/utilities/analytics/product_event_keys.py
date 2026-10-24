"""
Ids of product events: a step that happens once per subject gets an id
derived from the subject, so recording it twice (a retried request, two
processes, the daily reconciliation) stores it once; every other step gets
a random id.
"""

from uuid import UUID, uuid5

from app.schemas.constants.analytics import ProductEventName
from app.schemas.dto.analytics.product_event_drafts import ProductEventDraft
from app.schemas.typings.analytics.prefixed_id import ProductEventId

# Fixed namespace of the derived ids (never change it: stored ids and the
# once-only steps depend on it).
PRODUCT_EVENT_NAMESPACE: UUID = UUID("6f1c2a9e-4b7d-4e35-9a0c-8d2f5e1b7c43")

ONCE_PER_USER: frozenset[ProductEventName] = frozenset({ProductEventName.SIGNED_UP})
ONCE_PER_BUSINESS: frozenset[ProductEventName] = frozenset(
    {
        ProductEventName.BUSINESS_CREATED,
        ProductEventName.TEST_CHAT_TRIED,
        ProductEventName.WENT_LIVE,
        ProductEventName.FIRST_REAL_CONVERSATION,
        ProductEventName.FIRST_BOOKING,
        ProductEventName.FIRST_HANDOFF,
        ProductEventName.TRIAL_STARTED,
    }
)


def derive_product_event_id(draft: ProductEventDraft) -> ProductEventId:
    """
    The id of a step: derived for a once-only step (signing up per user;
    the business milestones and the trial per business; a channel kind's
    first connection and an agreement version per business), random
    otherwise.
    """

    subject: str | None = once_only_subject(draft)
    if subject is None:
        return ProductEventId()

    return ProductEventId(
        uuid5(PRODUCT_EVENT_NAMESPACE, f"{draft.name.value}|{subject}")
    )


def once_only_subject(draft: ProductEventDraft) -> str | None:
    """What a once-only step happens once for; None for a repeatable step."""

    if draft.name in ONCE_PER_USER and draft.user_id is not None:
        return str(draft.user_id)

    if draft.business_id is None:
        return None

    if draft.name in ONCE_PER_BUSINESS:
        return str(draft.business_id)

    if (
        draft.name is ProductEventName.CHANNEL_CONNECTED
        and draft.properties.channel is not None
    ):
        return f"{draft.business_id}|{draft.properties.channel.value}"

    if (
        draft.name is ProductEventName.DPA_ACCEPTED
        and draft.properties.dpa_version is not None
    ):
        return f"{draft.business_id}|{draft.properties.dpa_version}"

    return None

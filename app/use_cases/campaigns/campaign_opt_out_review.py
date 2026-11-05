"""
The opt-out rate of a business's campaign (ABUSE-05): of the customers its
messages of the last 30 days reached, how many asked for no more messages
since (a STOP in the message's chat, or their marketing consent taken
back). Bulk senders' rules (Gmail, Yahoo, WhatsApp quality) treat such a
rate as the sign of spam, so a campaign past it is held for the platform
team's review instead of writing on, and its owners are told why.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.constants.campaigns import CampaignMessageStatus
from app.schemas.domain.campaigns import CampaignMessageDocument, CampaignReviewHold
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.paging import KeysetPosition, KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.campaigns.constrained_integers import CampaignMessageCount
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.utilities.paging.keyset_paging import single_value_position

MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
REVIEW_WINDOW_DAYS: int = 30
# A rate means something only from this many messages, and a hold needs
# at least this many customers who opted out.
MIN_SENT_FOR_REVIEW: int = 40
MIN_OPTED_OUT_FOR_REVIEW: int = 3
# The share of reached customers (percent) that opted out, from which the
# campaign is held.
OPT_OUT_PERCENT_FOR_REVIEW: int = 5
PAGE_SIZE: KeysetReadLimit = KeysetReadLimit(200)
REACHED_STATUSES: frozenset[CampaignMessageStatus] = frozenset(
    {CampaignMessageStatus.SENT, CampaignMessageStatus.BOOKED}
)


@dataclass(frozen=True)
class CampaignOptOutRate:
    """Customers reached in the window, and those of them who opted out since."""

    sent: CampaignMessageCount
    opted_out: CampaignMessageCount

    def needs_review(self) -> bool:
        return (
            int(self.sent) >= MIN_SENT_FOR_REVIEW
            and int(self.opted_out) >= MIN_OPTED_OUT_FOR_REVIEW
            and 100 * int(self.opted_out) >= OPT_OUT_PERCENT_FOR_REVIEW * int(self.sent)
        )

    def hold(self, now: Microseconds) -> CampaignReviewHold:
        return CampaignReviewHold(held_at=now, sent=self.sent, opted_out=self.opted_out)


def measure_opt_outs(
    message_repo: CampaignMessageRepoContract,
    contact_repo: ContactRepoContract,
    business_id: BusinessId,
    now: Microseconds,
    released_at: Microseconds | None = None,
) -> CampaignOptOutRate:
    """
    Walk the business's messages newest first, a page of 200 at a time,
    until the window ends (30 days, or the last release of a hold when it
    is later: a released campaign starts afresh); each page's customers
    come in one read.
    """

    since: int = int(now) - REVIEW_WINDOW_DAYS * MICROSECONDS_PER_DAY
    if released_at is not None:
        since = max(since, int(released_at))
    reached: dict[ContactId, CampaignMessageDocument] = {}
    after: KeysetPosition | None = None
    while True:
        page: list[CampaignMessageDocument] = message_repo.page_latest(
            business_id, KeysetSlice(after=after, limit=PAGE_SIZE)
        )
        for message in page:
            if (
                message.status in REACHED_STATUSES
                and message.sent_at is not None
                and int(message.sent_at) >= since
                and message.contact_id not in reached
            ):
                reached[message.contact_id] = message

        if len(page) < int(PAGE_SIZE) or int(page[-1].created_at) < since:
            break

        after = single_value_position(int(page[-1].created_at), str(page[-1].id))

    contacts: dict[ContactId, ContactDocument] = contact_repo.get_many(
        business_id, list(reached)
    )
    opted_out: int = len(
        [
            message
            for contact_id, message in reached.items()
            if contact_id in contacts
            and has_opted_out_since(contacts[contact_id], message)
        ]
    )
    return CampaignOptOutRate(
        sent=CampaignMessageCount(len(reached)),
        opted_out=CampaignMessageCount(opted_out),
    )


def has_opted_out_since(
    contact: ContactDocument, message: CampaignMessageDocument
) -> bool:
    """
    A STOP in the chat the message went to (a STOP before it would have
    stopped the message), or the marketing consent taken back after it.
    """

    consent = contact.marketing_consent
    return (
        message.channel is not None and message.channel in contact.opted_out_channels
    ) or (
        consent is not None
        and consent.withdrawn_at is not None
        and message.sent_at is not None
        and int(consent.withdrawn_at) >= int(message.sent_at)
    )

"""
Feedback after visits in a demo business: the settings (on, two hours
after the visit, the WhatsApp template) and a request for each visit of
the month that ended before today, with the answers a busy place gets:
mostly fives, an occasional low score, a few unanswered, one customer who
had replied STOP, and some who opened the review link.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.feedback import FeedbackRequestStatus, FeedbackSkipReason
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.feedback import FeedbackRequestDocument, ReviewSettingsDocument
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.feedback.constrained_integers import (
    FeedbackDelayMinutes,
    ReviewLinkClickCount,
    VisitScore,
)
from app.utilities.feedback.feedback_keys import (
    feedback_request_id_of,
    new_review_token,
    review_settings_id_of,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
DELAY_MINUTES: int = 120
ASKED_AFTER_MICROSECONDS: int = DELAY_MINUTES * 60 * MICROSECONDS_PER_SECOND
ANSWERED_AFTER_MICROSECONDS: int = 25 * 60 * MICROSECONDS_PER_SECOND
CLICKED_AFTER_MICROSECONDS: int = 3 * 60 * MICROSECONDS_PER_SECOND
MESSENGERS: frozenset[ChannelKind] = frozenset(
    {
        ChannelKind.TELEGRAM,
        ChannelKind.WHATSAPP,
        ChannelKind.MESSENGER,
        ChannelKind.INSTAGRAM,
    }
)
# (score, review link visits) of each answered visit in turn; None: no answer.
OUTCOMES: tuple[tuple[int, int] | None, ...] = (
    (5, 1),
    (5, 2),
    (4, 0),
    None,
    (5, 1),
    (2, 0),
    (5, 0),
    (4, 1),
    None,
    (3, 0),
)


def build_demo_review_settings(
    business: BusinessDocument, now: Microseconds
) -> ReviewSettingsDocument:
    return ReviewSettingsDocument(
        id=review_settings_id_of(business.id),
        business_id=business.id,
        is_feedback_enabled=True,
        delay_minutes=FeedbackDelayMinutes(DELAY_MINUTES),
        feedback_template_name=WhatsAppTemplateName("visit_feedback"),
        created_at=business.created_at,
        updated_at=now,
    )


def build_demo_feedback_requests(
    business: BusinessDocument,
    bookings: Sequence[BookingDocument],
    contacts: Sequence[ContactDocument],
    now: Microseconds,
) -> list[FeedbackRequestDocument]:
    """A request for every real visit asked about before now, oldest first."""

    by_id: dict[ContactId, ContactDocument] = {item.id: item for item in contacts}
    visits: list[BookingDocument] = sorted(
        (
            booking
            for booking in bookings
            if booking.status in (BookingStatus.COMPLETED, BookingStatus.CONFIRMED)
            and not booking.is_sandbox
            and asked_at(booking) < int(now)
        ),
        key=lambda booking: (int(booking.ends_at), str(booking.id)),
    )
    return [
        build_request(business, visit, by_id.get(visit.contact_id), index)
        for index, visit in enumerate(visits)
    ]


def asked_at(booking: BookingDocument) -> int:
    return int(booking.ends_at) * MICROSECONDS_PER_SECOND + ASKED_AFTER_MICROSECONDS


def build_request(
    business: BusinessDocument,
    visit: BookingDocument,
    contact: ContactDocument | None,
    index: int,
) -> FeedbackRequestDocument:
    moment = Microseconds(asked_at(visit))
    request = FeedbackRequestDocument(
        id=feedback_request_id_of(business.id, visit.id),
        business_id=business.id,
        booking_id=visit.id,
        contact_id=visit.contact_id,
        visit_ended_at=Microseconds(int(visit.ends_at) * MICROSECONDS_PER_SECOND),
        language=visit.language or business.default_language,
        status=FeedbackRequestStatus.SENT,
        created_at=moment,
        updated_at=moment,
    )
    if contact is not None and contact.opted_out_channels:
        request.status = FeedbackRequestStatus.SKIPPED
        request.skip_reason = FeedbackSkipReason.OPTED_OUT
        return request

    request.channel = (
        visit.source_channel
        if visit.source_channel in MESSENGERS
        else ChannelKind.WHATSAPP
    )
    request.review_token = new_review_token()
    request.sent_at = moment
    request.delivered_at = moment
    outcome: tuple[int, int] | None = OUTCOMES[index % len(OUTCOMES)]
    if outcome is None:
        return request

    score, clicks = outcome
    answered = Microseconds(int(moment) + ANSWERED_AFTER_MICROSECONDS)
    request.status = FeedbackRequestStatus.ANSWERED
    request.score = VisitScore(score)
    request.answered_at = answered
    request.updated_at = answered
    request.review_clicks = ReviewLinkClickCount(clicks)
    if clicks:
        request.first_clicked_at = Microseconds(
            int(answered) + CLICKED_AFTER_MICROSECONDS
        )

    return request

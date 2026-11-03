"""
A provider's own words about a failed delivery reach platform admins only
(OWASP API3, API-05), through the application as it is wired: the owner
reads the channel, text-back and feedback-request lists with the plain
state (`status`, a channel's `last_error_reason`) and `last_error` null;
a platform admin looking into the same cabinet reads the provider's words.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackStatus,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.deliveries import DeliveryFailureReason
from app.schemas.constants.feedback import FeedbackRequestStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.feedback import FeedbackRequestDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import ChannelErrorSummary
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.calls.call_follow_up_keys import missed_call_id_of
from app.utilities.feedback.feedback_keys import feedback_request_id_of
from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL, JsonObject
from tests.e2e.journeys import sign_in_and_create_restaurant

PROVIDER_WORDS: str = "Telegram sendMessage failed (401): Unauthorized"


def store_failures(workshop: Workshop, business_id: BusinessId) -> None:
    """A refused Telegram bot, a failed text-back and a failed feedback request."""

    container = workshop.container
    now: Microseconds = workshop.clock.wall_clock.now_unix()
    call_id = ProviderCallId("pbx-provider-errors")
    booking_id = BookingId()
    with container.utilities.storage_scope().scoped_to_business(business_id):
        container.repositories.channel_repo().save(
            ChannelDocument(
                business_id=business_id,
                kind=ChannelKind.TELEGRAM,
                status=ChannelStatus.ERROR,
                last_error=ChannelErrorSummary(PROVIDER_WORDS),
                last_error_at=now,
                last_error_reason=DeliveryFailureReason.CREDENTIAL_REJECTED,
                created_at=now,
                updated_at=now,
            )
        )
        container.repositories.missed_call_repo().insert_if_new(
            MissedCallDocument(
                id=missed_call_id_of(business_id, MissedCallSource.PBX, call_id),
                business_id=business_id,
                source=MissedCallSource.PBX,
                provider_call_id=call_id,
                reason=MissedCallReason.NO_ANSWER,
                called_at=now,
                language=LanguageTag("en"),
                status=TextBackStatus.FAILED,
                last_error=DeliveryErrorText(PROVIDER_WORDS),
                created_at=now,
                updated_at=now,
            )
        )
        container.repositories.feedback_request_repo().insert_if_new(
            FeedbackRequestDocument(
                id=feedback_request_id_of(business_id, booking_id),
                business_id=business_id,
                booking_id=booking_id,
                contact_id=ContactId(),
                visit_ended_at=now,
                language=LanguageTag("en"),
                status=FeedbackRequestStatus.FAILED,
                last_error=DeliveryErrorText(PROVIDER_WORDS),
                created_at=now,
                updated_at=now,
            )
        )


def read_lists(workshop: Workshop, base: str, token: str) -> dict[str, JsonObject]:
    """The failed item of each list, as this person reads it."""

    channels = workshop.client.get(f"{base}/channels", headers=bearer(token))
    text_backs = workshop.client.get(f"{base}/text-backs", headers=bearer(token))
    requests = workshop.client.get(f"{base}/feedback-requests", headers=bearer(token))
    for response in (channels, text_backs, requests):
        assert response.status_code == 200, response.text

    [telegram] = [item for item in channels.json() if item["channel"] == "telegram"]
    [text_back] = text_backs.json()["items"]
    [request] = requests.json()["items"]
    return {"channel": telegram, "text_back": text_back, "request": request}


def test_only_a_platform_admin_reads_the_providers_words(workshop: Workshop) -> None:
    owner, _, business_id = sign_in_and_create_restaurant(workshop)
    base = f"/v1/businesses/{business_id}"
    store_failures(workshop, BusinessId(business_id))

    by_owner = read_lists(workshop, base, owner)
    admin, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    opened = workshop.client.post(
        f"/v1/admin/clients/{business_id}/open",
        json={"reason": "A customer says the bot does not answer"},
        headers=bearer(admin),
    )
    assert opened.status_code == 200, opened.text
    by_admin = read_lists(workshop, base, admin)

    assert PROVIDER_WORDS not in str(by_owner)
    assert {name: item["last_error"] for name, item in by_owner.items()} == {
        "channel": None,
        "text_back": None,
        "request": None,
    }
    # The owner still learns what failed, in the cabinet's terms.
    assert by_owner["channel"]["status"] == "error"
    assert by_owner["channel"]["last_error_reason"] == "credential_rejected"
    assert by_owner["text_back"]["status"] == "failed"
    assert by_owner["request"]["status"] == "failed"
    assert {name: item["last_error"] for name, item in by_admin.items()} == {
        "channel": PROVIDER_WORDS,
        "text_back": PROVIDER_WORDS,
        "request": PROVIDER_WORDS,
    }

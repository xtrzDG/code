"""
Sending a text-back's SMS and storing how a text-back went on the missed
call (its WhatsApp template goes through the outbox, `text_back_whatsapp`).
"""

from collections.abc import Callable

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.messaging_clients import SmsMessagingClientContract
from app.contracts.repositories.call_follow_up_repositories import (
    MissedCallRepoContract,
)
from app.schemas.constants.calls import (
    TextBackChannel,
    TextBackSkipReason,
    TextBackStatus,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.exceptions.application_errors import DeliveryNotConfiguredError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.strings import SmsMessageText
from app.utilities.calls.text_back_texts import TEXT_BACK_SMS_TEXT
from app.utilities.deliveries.retry_policy import (
    RETRYABLE_FAILURES,
    classify_delivery_error,
)


def is_retryable_failure(error: ApplicationError) -> bool:
    """A rate limit or a temporary provider failure: worth another attempt."""

    return classify_delivery_error(error) in RETRYABLE_FAILURES


class TextBackSms:
    """The SMS leg of a text-back, from the platform's sender."""

    def __init__(
        self,
        sms_client: SmsMessagingClientContract | None,
        text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._sms_client: SmsMessagingClientContract | None = sms_client
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def send(
        self,
        business: BusinessDocument,
        missed: MissedCallDocument,
        caller: E164PhoneNumber,
    ) -> None:
        """Raises what the provider refused (or that none is configured)."""

        if self._sms_client is None:
            raise DeliveryNotConfiguredError("No SMS provider is configured.")

        text: str = str(
            self._text_resolver.resolve(TEXT_BACK_SMS_TEXT, missed.language)
        ).format(business=business.name)
        self._sms_client.send_sms(caller, SmsMessageText(text))


class TextBackSettlement:
    """
    How a text-back ended, stored only while it is still QUEUED (a job that
    ran twice never overwrites what the first one stored).
    """

    def __init__(
        self,
        missed_call_repo: MissedCallRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._missed_call_repo: MissedCallRepoContract = missed_call_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def sent(
        self, missed: MissedCallDocument, channel: TextBackChannel
    ) -> MissedCallDocument:
        now: Microseconds = self._wall_clock.now_unix()

        def change(current: MissedCallDocument) -> MissedCallDocument:
            current.status = TextBackStatus.SENT
            current.channel = channel
            current.sent_at = now
            return current

        return self._while_queued(missed, change)

    def skip(
        self, missed: MissedCallDocument, reason: TextBackSkipReason
    ) -> MissedCallDocument:
        def change(current: MissedCallDocument) -> MissedCallDocument:
            current.status = TextBackStatus.SKIPPED
            current.skip_reason = reason
            return current

        return self._while_queued(missed, change)

    def fail(
        self, missed: MissedCallDocument, error: DeliveryErrorText | None
    ) -> MissedCallDocument:
        def change(current: MissedCallDocument) -> MissedCallDocument:
            current.status = TextBackStatus.FAILED
            current.last_error = error
            return current

        return self._while_queued(missed, change)

    def switch_to_sms(
        self, missed: MissedCallDocument, error: DeliveryErrorText | None
    ) -> MissedCallDocument:
        """WhatsApp refused it for good: the next attempts go by SMS."""

        def change(current: MissedCallDocument) -> MissedCallDocument:
            current.channel = TextBackChannel.SMS
            current.last_error = error
            return current

        return self._while_queued(missed, change)

    def link(
        self, missed: MissedCallDocument, conversation_id: ConversationId
    ) -> MissedCallDocument:
        now: Microseconds = self._wall_clock.now_unix()

        def change(current: MissedCallDocument) -> MissedCallDocument:
            current.conversation_id = conversation_id
            current.updated_at = now
            return current

        return (
            self._missed_call_repo.update(missed.business_id, missed.id, change)
            or missed
        )

    def _while_queued(
        self,
        missed: MissedCallDocument,
        change: Callable[[MissedCallDocument], MissedCallDocument],
    ) -> MissedCallDocument:
        now: Microseconds = self._wall_clock.now_unix()

        def apply(current: MissedCallDocument) -> MissedCallDocument | None:
            if current.status is not TextBackStatus.QUEUED:
                return None

            updated: MissedCallDocument = change(current)
            updated.updated_at = now
            return updated

        stored: MissedCallDocument | None = self._missed_call_repo.update(
            missed.business_id, missed.id, apply
        )
        if stored is not None:
            return stored

        return self._missed_call_repo.get(missed.business_id, missed.id) or missed

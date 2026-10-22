import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deliveries import InboundEventKind, OutboundMessageKind
from app.schemas.domain.channels import ChannelDocument, InstagramCommentReplies
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
)
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import (
    RateLimitedError,
    ValidationFailedError,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey
from app.schemas.typings.meta_connection.constrained_strings import MetaCommentId
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.shared.outbox_queue import queue_outbound_message
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.comment_keywords import matching_keyword
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
)

logger: logging.Logger = logging.getLogger(__name__)

# Instagram answers an account's private replies at a modest pace; a viral
# post's hundreds of comments are answered at most this many an hour, and
# one person at most once a day (a second keyword comment is left alone).
REPLIES_PER_BUSINESS_PER_HOUR: RequestsPerWindow = RequestsPerWindow(60)
HOUR: RateWindowSeconds = RateWindowSeconds(60 * 60)
REPLIES_PER_AUTHOR_PER_DAY: RequestsPerWindow = RequestsPerWindow(1)
DAY: RateWindowSeconds = RateWindowSeconds(24 * 60 * 60)


class ReplyToCommentTriggerUseCase(UseCaseContract[InboundEventClaim, InboundAnswer]):
    """
    `process_comment_trigger`, after the worker took the event: the
    Instagram account's private reply to a comment that named the owner's
    keyword goes into the outbox (one message per comment, sent with
    retries by `deliver_outbound` through Instagram's private replies).

    The owner's settings are read again: a reply turned off or a keyword
    removed meanwhile ends the event without a message. At most 60 replies
    an hour per business and one per author a day are sent; a comment over
    either limit is refused (the event FAILED, nothing sent).
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
        unit_of_work: StorageUnitOfWorkContract | None = None,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._rate_limits: RequestRateLimitRegistryContract = rate_limit_registry
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work

    def run(self, input_data: InboundEventClaim) -> InboundAnswer:
        event: InboundEventDocument = input_data.event
        comment: InboundCustomerMessage | None = event.customer_message
        if (
            event.kind is not InboundEventKind.COMMENT_TRIGGER
            or comment is None
            or event.business_id is None
            or event.channel_id is None
        ):
            raise ValidationFailedError("The inbox event is not an Instagram comment.")

        channel: ChannelDocument | None = self._channel_repo.get(event.channel_id)
        replies: InstagramCommentReplies | None = (
            None if channel is None else channel.comment_replies
        )
        if (
            channel is None
            or channel.business_id != event.business_id
            or not is_channel_active(channel)
            or replies is None
            or not replies.is_on
            or replies.reply_text is None
            or matching_keyword(str(comment.text), list(replies.keywords)) is None
        ):
            logger.info("Comment %s needs no reply any more.", event.id)
            return InboundAnswer(event=event)

        comment_id = MetaCommentId(str(event.provider_message_id))
        idempotency_key = OutboundIdempotencyKey(f"comment_reply:{comment_id}")
        if (
            self._outbound_message_repo.get(
                event.business_id,
                derive_outbound_message_id(event.business_id, idempotency_key),
            )
            is not None
        ):
            return InboundAnswer(event=event)  # Queued by an earlier attempt.

        now: Microseconds = self._wall_clock.now_unix()
        author: RateLimitCounter = author_counter(event, comment)
        self._take_business_slot(event, author, now)
        self._queue(
            event,
            channel.id,
            comment,
            comment_id,
            idempotency_key,
            MessageText(str(replies.reply_text)),
            now,
        )
        # Counted once queued: an attempt that failed before can run again.
        self._rate_limits.try_acquire_all([author], DAY, now)
        return InboundAnswer(event=event)

    def _take_business_slot(
        self,
        event: InboundEventDocument,
        author: RateLimitCounter,
        now: Microseconds,
    ) -> None:
        """
        Refuse a reply over either limit, else count it against the
        business's hour (atomically across workers). One author's comments
        are processed one at a time (their serial key), so their daily
        limit cannot be raced.
        """

        if not self._rate_limits.has_room(author, DAY, now):
            raise RateLimitedError("This person got a private reply today already.")

        business = RateLimitCounter(
            key=RateLimitKey(f"comment-reply:business:{event.business_id}"),
            limit=REPLIES_PER_BUSINESS_PER_HOUR,
        )
        if self._rate_limits.try_acquire_all([business], HOUR, now) is not None:
            raise RateLimitedError("The hour's private replies are used up.")

    def _queue(
        self,
        event: InboundEventDocument,
        channel_id: ChannelId,
        comment: InboundCustomerMessage,
        comment_id: MetaCommentId,
        idempotency_key: OutboundIdempotencyKey,
        text: MessageText,
        now: Microseconds,
    ) -> None:
        if event.business_id is None:
            return

        queue_outbound_message(
            self._outbound_message_repo,
            self._job_queue,
            OutboundMessageDocument(
                id=derive_outbound_message_id(event.business_id, idempotency_key),
                business_id=event.business_id,
                kind=OutboundMessageKind.COMMENT_REPLY,
                idempotency_key=idempotency_key,
                recipient_key=customer_recipient_key(
                    channel_id, comment.channel_user_id
                ),
                customer=CustomerRecipient(
                    channel_id=channel_id,
                    channel=event.channel,
                    channel_user_id=comment.channel_user_id,
                    comment_id=comment_id,
                ),
                text=text,
                created_at=now,
                updated_at=now,
            ),
            self._unit_of_work,
        )


def author_counter(
    event: InboundEventDocument, comment: InboundCustomerMessage
) -> RateLimitCounter:
    """One private reply per person and business a day."""

    return RateLimitCounter(
        key=RateLimitKey(
            f"comment-reply:author:{event.business_id}:{comment.channel_user_id}"
        ),
        limit=REPLIES_PER_AUTHOR_PER_DAY,
    )

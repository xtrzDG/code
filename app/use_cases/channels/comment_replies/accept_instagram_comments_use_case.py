import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import ChannelAdapterContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.channels import ChannelDocument, InstagramCommentReplies
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.dto.channels.channel_webhooks import MetaWebhookRequest
from app.schemas.dto.channels.comment_replies import InstagramComment
from app.schemas.dto.deliveries import InboxIntake
from app.schemas.typings.channels.constrained_integers import WebhookMessageCount
from app.schemas.typings.channels.strings import ProviderMessageId
from app.use_cases.shared.inbox_queue import store_and_queue
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.comment_keywords import matching_keyword
from app.utilities.channels.instagram_comments import read_instagram_comments
from app.utilities.deliveries.comment_trigger_jobs import PROCESS_COMMENT_TRIGGER_JOB
from app.utilities.deliveries.delivery_keys import (
    derive_inbound_event_id,
    inbound_serial_key,
)
from app.utilities.storage.release_gates import COMMENT_REPLIES_GATE, is_gate_open

logger: logging.Logger = logging.getLogger(__name__)


class AcceptInstagramCommentsUseCase(UseCaseContract[MetaWebhookRequest, InboxIntake]):
    """
    The comments of Meta's Instagram webhook (the `comments` field, signed
    with META_APP_SECRET like its messages): a new comment under the posts
    of an account whose comment-to-DM is on, that holds one of the owner's
    keywords and was not written by the account itself, is stored in the
    inbox as a COMMENT_TRIGGER event and `process_comment_trigger` is
    queued (the author's messages one at a time). Every other comment is
    left alone, and nothing of it is stored.

    The comment's id is the event's platform id, so a redelivered webhook
    finds its event and the comment is answered once. Until the release
    gate of comment replies opens (the next release), comments are only
    read.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        instagram_adapter: ChannelAdapterContract,
        inbound_event_repo: InboundEventRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        unit_of_work: StorageUnitOfWorkContract | None = None,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._instagram_adapter: ChannelAdapterContract = instagram_adapter
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work

    def run(self, input_data: MetaWebhookRequest) -> InboxIntake:
        comments: list[InstagramComment] = read_instagram_comments(
            input_data.payload.body
        )
        if not comments:
            return InboxIntake()

        self._instagram_adapter.verify_signature(input_data.payload, None)
        if not is_gate_open(COMMENT_REPLIES_GATE):
            logger.info(
                "%d Instagram comments read; comment replies start with the "
                "next release.",
                len(comments),
            )
            return InboxIntake()

        now: Microseconds = self._wall_clock.now_unix()
        triggers: list[InboundEventDocument] = [
            event
            for comment in comments
            if (event := self._trigger_of(comment, now)) is not None
        ]
        queued: int = sum(1 for event in triggers if self._store(event))
        return InboxIntake(
            received=WebhookMessageCount(len(triggers)),
            queued=WebhookMessageCount(queued),
            duplicates=WebhookMessageCount(len(triggers) - queued),
        )

    def _trigger_of(
        self, comment: InstagramComment, now: Microseconds
    ) -> InboundEventDocument | None:
        """The inbox event of a comment that asks for a private reply."""

        channel: ChannelDocument | None = self._channel_repo.find_by_external_id(
            ChannelKind.INSTAGRAM, comment.account_id
        )
        replies: InstagramCommentReplies | None = (
            None if channel is None else channel.comment_replies
        )
        if (
            channel is None
            or replies is None
            or not replies.is_on
            or replies.reply_text is None
            or not is_channel_active(channel)
            or matching_keyword(str(comment.text), list(replies.keywords)) is None
        ):
            return None

        provider_message_id = ProviderMessageId(str(comment.comment_id))
        return InboundEventDocument(
            id=derive_inbound_event_id(
                channel.business_id, ChannelKind.INSTAGRAM, provider_message_id
            ),
            business_id=channel.business_id,
            kind=InboundEventKind.COMMENT_TRIGGER,
            channel=ChannelKind.INSTAGRAM,
            channel_id=channel.id,
            provider_message_id=provider_message_id,
            customer_message=InboundCustomerMessage(
                channel_user_id=comment.author_id,
                text=comment.text,
                contact_name=comment.author_username,
            ),
            created_at=now,
            updated_at=now,
        )

    def _store(self, event: InboundEventDocument) -> bool:
        message: InboundCustomerMessage | None = event.customer_message
        return store_and_queue(
            self._inbound_event_repo,
            self._job_queue,
            event,
            PROCESS_COMMENT_TRIGGER_JOB,
            None
            if message is None
            else inbound_serial_key(
                event.business_id, event.channel, str(message.channel_user_id)
            ),
            unit_of_work=self._unit_of_work,
        )

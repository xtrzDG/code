from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import VoiceWebhookAdapterContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.voice_webhooks import (
    FinishedCallReport,
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.deliveries.strings import InboundPayloadText
from app.use_cases.channels.inbox.inbox_queue import store_and_queue
from app.utilities.deliveries.delivery_jobs import PROCESS_POST_CALL_JOB
from app.utilities.deliveries.delivery_keys import derive_inbound_event_id


class AcceptPostCallWebhookUseCase(
    UseCaseContract[PostCallWebhookRequest, PostCallWebhookOutcome]
):
    """
    Post-call webhook of the voice platform, acknowledged at once: check
    the signature (HMAC, at most 30 minutes old) and that the body is a
    finished-call report, keep it in the inbox and queue
    `process_post_call` (the worker stores the call, bills it and confirms
    a booking to the caller). Other events are ignored; a report the
    platform delivered before is a duplicate.
    """

    def __init__(
        self,
        voice_webhook_adapter: VoiceWebhookAdapterContract,
        inbound_event_repo: InboundEventRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._voice_webhook_adapter: VoiceWebhookAdapterContract = voice_webhook_adapter
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PostCallWebhookRequest) -> PostCallWebhookOutcome:
        now: Microseconds = self._wall_clock.now_unix()
        self._voice_webhook_adapter.verify_post_call_signature(input_data, now)
        report: FinishedCallReport | None = self._voice_webhook_adapter.parse_post_call(
            input_data.body
        )
        if report is None:
            return PostCallWebhookOutcome(status=PostCallEventStatus.IGNORED)

        try:
            payload = InboundPayloadText(input_data.body.decode("utf-8"))
        except UnicodeDecodeError as error:
            raise ValidationFailedError(
                "The post-call webhook is not UTF-8 JSON."
            ) from error

        provider_message_id = ProviderMessageId(str(report.provider_call_id))
        event = InboundEventDocument(
            id=derive_inbound_event_id(None, ChannelKind.PHONE, provider_message_id),
            kind=InboundEventKind.VOICE_POST_CALL,
            channel=ChannelKind.PHONE,
            provider_message_id=provider_message_id,
            payload=payload,
            created_at=now,
            updated_at=now,
        )
        is_new: bool = store_and_queue(
            self._inbound_event_repo,
            self._job_queue,
            event,
            PROCESS_POST_CALL_JOB,
            None,
        )
        return PostCallWebhookOutcome(
            status=(
                PostCallEventStatus.QUEUED if is_new else PostCallEventStatus.DUPLICATE
            )
        )

from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import ChannelAdapterContract
from app.contracts.repositories import ChannelRepoContract, UsageEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels import ChannelReplyDelivery
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
)
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.utilities.channels.channel_health import (
    mark_channel_failing,
    mark_channel_working,
)
from app.utilities.channels.delivery_targets import (
    build_whatsapp_usage_event,
    find_business_channel,
)


class DeliverChannelReplyUseCase(
    UseCaseContract[ChannelReplyDelivery, DeliveredMessageCount]
):
    """
    Send an assistant reply back through the channel the customer wrote in.

    Long replies are split at the channel's limit by its adapter. WhatsApp
    replies are metered as usage events (concept usage_events wa_reply).
    When the platform refuses the channel's credential the channel is put
    in ERROR with the reason (and the error is raised again); a delivered
    reply clears that state.
    """

    def __init__(
        self,
        telegram_adapter: ChannelAdapterContract,
        whatsapp_adapter: ChannelAdapterContract,
        messenger_adapter: ChannelAdapterContract,
        instagram_adapter: ChannelAdapterContract,
        usage_event_repo: UsageEventRepoContract,
        channel_repo: ChannelRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._adapters: dict[ChannelKind, ChannelAdapterContract] = {
            ChannelKind.TELEGRAM: telegram_adapter,
            ChannelKind.WHATSAPP: whatsapp_adapter,
            ChannelKind.MESSENGER: messenger_adapter,
            ChannelKind.INSTAGRAM: instagram_adapter,
        }
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ChannelReplyDelivery) -> DeliveredMessageCount:
        adapter: ChannelAdapterContract | None = self._adapters.get(
            input_data.target.channel
        )
        if adapter is None:
            raise ExternalServiceError(
                f"Replies cannot be sent through {input_data.target.channel.value}."
            )

        try:
            delivered: DeliveredMessageCount = adapter.send(
                input_data.target,
                input_data.text,
            )
        except ChannelCredentialRejectedError as error:
            self._record_health(input_data, str(error))
            raise

        self._record_health(input_data, None)
        if input_data.target.channel is ChannelKind.WHATSAPP and delivered > 0:
            self._usage_event_repo.append(
                build_whatsapp_usage_event(
                    input_data.business_id,
                    input_data.conversation_id,
                    delivered,
                    self._wall_clock.now_unix(),
                )
            )

        return delivered

    def _record_health(
        self,
        input_data: ChannelReplyDelivery,
        failure: str | None,
    ) -> None:
        channel: ChannelDocument | None = find_business_channel(
            self._channel_repo,
            input_data.business_id,
            input_data.target.channel,
        )
        if channel is None:
            return

        now: Microseconds = self._wall_clock.now_unix()
        if failure is None:
            mark_channel_working(self._channel_repo, channel, now)
        else:
            mark_channel_failing(self._channel_repo, channel, failure, now)

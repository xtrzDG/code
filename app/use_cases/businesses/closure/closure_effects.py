"""What closing a business switches off, and what cancelling the closure brings back."""

import logging

from typed_time_provider import Microseconds

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.use_cases.shared.billing_records import find_current_subscription
from app.use_cases.shared.recurring_charges import stop_recurring_charges

logger: logging.Logger = logging.getLogger(__name__)


class ClosureEffects:
    """
    Closing pauses the assistant (a live one: calls are refused and the
    voice agent goes) and turns every connected channel off, keeping its
    credentials and its account, so nobody else takes the account while the
    business may still come back. An owner's closure also stops the
    automatic charges and cancels the subscription (no charge during the
    30 days; the period already paid keeps running); a provider that cannot
    be reached leaves the subscription as it is, and the deletion stops the
    charges for certain (it retries until the provider answers). Cancelling the
    closure turns the same channels on again and resumes an assistant that
    was live (activating its published version anew); billing stays
    stopped until the owner chooses a plan again.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        subscription_repo: SubscriptionRepoContract,
        payment_gateway: PaymentGatewayAdapterContract,
        payment_order_repo: PaymentOrderRepoContract,
        remove_voice_agent: UseCaseContract[BusinessId, None],
        resume_assistant: UseCaseContract[BusinessDocument, None],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._remove_voice_agent: UseCaseContract[BusinessId, None] = remove_voice_agent
        self._resume_assistant: UseCaseContract[BusinessDocument, None] = (
            resume_assistant
        )

    def pause(self, business_id: BusinessId, now: Microseconds) -> None:
        """The assistant stops answering; its voice agent goes."""

        def pause_live(current: BusinessDocument) -> None:
            if current.status is BusinessStatus.LIVE:
                current.status = BusinessStatus.PAUSED
                current.updated_at = now

        self._business_repo.update(business_id, pause_live)
        self._remove_voice_agent.run(business_id)

    def disconnect_channels(
        self, business_id: BusinessId, now: Microseconds
    ) -> list[ChannelId]:
        """Every connected customer channel off; the ones turned off."""

        def switch_off(channel: ChannelDocument) -> ChannelDocument | None:
            if channel.status is not ChannelStatus.CONNECTED:
                return None

            channel.status = ChannelStatus.DISABLED
            channel.updated_at = now
            return channel

        return [
            channel.id
            for channel in self._channel_repo.list_by_business(business_id)
            if channel.kind is not ChannelKind.OWNER_TEST
            and self._channel_repo.modify(business_id, channel.id, switch_off)
            is not None
        ]

    def stop_billing(self, business_id: BusinessId, now: Microseconds) -> None:
        """No automatic charge any more; the subscription is cancelled."""

        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo, business_id
        )
        if subscription is None or subscription.status is SubscriptionStatus.CANCELLED:
            return

        try:
            stop_recurring_charges(
                self._payment_gateway, self._payment_order_repo, subscription
            )
        except ExternalServiceError as error:
            logger.warning(
                "The automatic charges of business %s were not stopped at its "
                "closure: %s",
                business_id,
                error,
            )
            return

        subscription.status = SubscriptionStatus.CANCELLED
        subscription.grace_until = None
        subscription.pause_starts_at = None
        subscription.pause_until = None
        subscription.updated_at = now
        self._subscription_repo.save(subscription)

    def restore(self, closure: BusinessClosureDocument, now: Microseconds) -> None:
        """The channels the closure turned off on again; a live assistant resumed."""

        def switch_on(channel: ChannelDocument) -> ChannelDocument | None:
            if channel.status is not ChannelStatus.DISABLED or (
                channel.external_id is None and channel.kind is not ChannelKind.WEB_CHAT
            ):
                return None

            channel.status = ChannelStatus.CONNECTED
            channel.updated_at = now
            return channel

        for channel_id in closure.disconnected_channel_ids:
            self._channel_repo.modify(closure.business_id, channel_id, switch_on)

        business: BusinessDocument | None = self._business_repo.get(closure.business_id)
        if (
            business is not None
            and closure.status_before is BusinessStatus.LIVE
            and business.status is BusinessStatus.PAUSED
        ):
            self._resume_assistant.run(business)

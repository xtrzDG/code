"""What a deleted business had at the providers, switched off before its data goes."""

import logging

from typed_time_provider import Microseconds

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.phone_numbers import (
    PhoneLineLockRegistryContract,
    PhoneNumberProvisionerAdapterContract,
    PhoneNumberRepoContract,
)
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.business_closures import DeprovisionTarget
from app.schemas.constants.payments import PaymentProvider
from app.schemas.constants.phone_numbers import PhoneNumberStatus
from app.schemas.domain.business_closures import DeprovisionRecord
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.dto.operations.calendar_connection import (
    CalendarDisconnectResult,
    DisconnectCalendarCommand,
)
from app.schemas.dto.phone_numbers.provisioning import PhoneNumberRelease
from app.schemas.exceptions.payment_errors import PaymentsNotConfiguredError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.businesses.deletion.channel_deprovisioning import (
    ChannelDeprovisioner,
    deprovision_record,
)

logger: logging.Logger = logging.getLogger(__name__)
GIVEN_BACK: frozenset[PhoneNumberStatus] = frozenset(
    {PhoneNumberStatus.ACTIVE, PhoneNumberStatus.RELEASING}
)


class BusinessDeprovisioner:
    """
    Everything the business had outside the platform, switched off before
    its rows go (so the credentials that reach it still exist): the voice
    agent, the channels' webhooks and subscriptions (`ChannelDeprovisioner`),
    Google Calendar access (revoked), rented numbers (returned to the
    carrier: no rental month bills again) and automatic payments (stopped at
    the provider). What costs money is strict: a number the carrier does not
    take back, or a charge schedule the provider does not stop, raises
    ExternalServiceError and the deletion job retries until it does; a
    provider that is not configured at all on this server cannot charge
    through it and is reported SKIPPED. Each step is safe to repeat.
    """

    def __init__(
        self,
        channels: ChannelDeprovisioner,
        channel_repo: ChannelRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        remove_voice_agent: UseCaseContract[BusinessId, None],
        disconnect_google_calendar: UseCaseContract[
            DisconnectCalendarCommand, CalendarDisconnectResult
        ],
        phone_number_repo: PhoneNumberRepoContract,
        phone_number_provisioner: PhoneNumberProvisionerAdapterContract,
        phone_line_lock: PhoneLineLockRegistryContract,
        subscription_repo: SubscriptionRepoContract,
        payment_gateway: PaymentGatewayAdapterContract,
    ) -> None:
        self._channels: ChannelDeprovisioner = channels
        self._channel_repo: ChannelRepoContract = channel_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._remove_voice_agent: UseCaseContract[BusinessId, None] = remove_voice_agent
        self._disconnect_google_calendar: UseCaseContract[
            DisconnectCalendarCommand, CalendarDisconnectResult
        ] = disconnect_google_calendar
        self._phone_number_repo: PhoneNumberRepoContract = phone_number_repo
        self._provisioner: PhoneNumberProvisionerAdapterContract = (
            phone_number_provisioner
        )
        self._phone_line_lock: PhoneLineLockRegistryContract = phone_line_lock
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway

    def deprovision(
        self, business_id: BusinessId, now: Microseconds
    ) -> list[DeprovisionRecord]:
        channels = self._channel_repo.list_by_business(business_id)
        return [
            self._voice_agent(business_id),
            self._channels.telegram(channels),
            self._channels.meta(channels),
            self._google_calendar(business_id),
            self._phone_numbers(business_id, now),
            self._payments(business_id),
        ]

    def _voice_agent(self, business_id: BusinessId) -> DeprovisionRecord:
        before: int = self._agent_count(business_id)
        if before:
            self._remove_voice_agent.run(business_id)

        left: int = self._agent_count(business_id)
        return deprovision_record(DeprovisionTarget.VOICE_AGENT, before - left, left)

    def _agent_count(self, business_id: BusinessId) -> int:
        return len(
            {
                version.voice_agent_id
                for version in self._assistant_version_repo.list_by_business(
                    business_id
                )
                if version.voice_agent_id is not None
            }
        )

    def _google_calendar(self, business_id: BusinessId) -> DeprovisionRecord:
        result: CalendarDisconnectResult = self._disconnect_google_calendar.run(
            DisconnectCalendarCommand(business_id=business_id)
        )
        return deprovision_record(
            DeprovisionTarget.GOOGLE_CALENDAR, int(bool(result.was_connected)), 0
        )

    def _phone_numbers(
        self, business_id: BusinessId, now: Microseconds
    ) -> DeprovisionRecord:
        with self._phone_line_lock.lock_for(business_id):
            held: PhoneNumberDocument | None = self._phone_number_repo.find_held(
                business_id
            )
            if held is None or held.status not in GIVEN_BACK:
                return deprovision_record(DeprovisionTarget.PHONE_NUMBER, 0, 0)

            self._provisioner.release_number(
                PhoneNumberRelease(
                    provider_number_id=held.provider_number_id,
                    voice_platform_number_id=held.voice_platform_number_id,
                )
            )
            self._phone_number_repo.modify(
                business_id,
                held.id,
                lambda current: current.model_copy(
                    update={
                        "status": PhoneNumberStatus.RELEASED,
                        "released_at": now,
                        "updated_at": now,
                    }
                ),
            )
        return deprovision_record(DeprovisionTarget.PHONE_NUMBER, 1, 0)

    def _payments(self, business_id: BusinessId) -> DeprovisionRecord:
        stopped: int = 0
        skipped: int = 0
        for subscription in self._subscription_repo.list_by_business(business_id):
            if subscription.provider_reference is None:
                continue

            try:
                self._payment_gateway.stop_recurring(
                    subscription.payment_provider or PaymentProvider.FLITT,
                    subscription.provider_reference,
                )
                stopped += 1
            except PaymentsNotConfiguredError as error:
                skipped += 1
                logger.error(
                    "The automatic charges of deleted business %s were not "
                    "stopped: payments are not configured here (%s).",
                    business_id,
                    error,
                )

        return deprovision_record(DeprovisionTarget.PAYMENT_SCHEDULE, stopped, skipped)

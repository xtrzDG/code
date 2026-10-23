"""
What the deletion switches off at the providers before the data goes:
money is strict (a number the carrier keeps, a charge schedule the provider
keeps, both fail the job so it retries), the rest is best effort and
reported honestly on the certificate.
"""

import pytest

from app.schemas.constants.business_closures import (
    DeprovisionOutcome,
    DeprovisionTarget,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.payments import PaymentProvider
from app.schemas.constants.phone_numbers import PhoneNumberStatus
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.payment_errors import PaymentsNotConfiguredError
from tests.business_closures.deprovisioning_fakes import (
    Gateway,
    MetaSubscriptions,
    Telegram,
)
from tests.business_closures.deprovisioning_world import (
    BUSINESS,
    NOW,
    UNREADABLE,
    channel,
    charging,
    deprovisioner,
    outcomes,
    rented,
    status_of,
    version,
)
from tests.phone_numbers.provisioner_fakes import FakePhoneNumberProvisioner


def test_a_business_without_providers_reports_nothing_everywhere() -> None:
    records = deprovisioner().deprovision(BUSINESS, NOW)

    assert {outcome for outcome, _ in outcomes(records).values()} == {
        DeprovisionOutcome.NOTHING
    }
    assert len(records) == len(DeprovisionTarget)


def test_bots_pages_and_own_whatsapp_accounts_are_unsubscribed() -> None:
    telegram, meta = Telegram(), MetaSubscriptions()
    channels = [
        channel(ChannelKind.TELEGRAM, "bot"),
        channel(ChannelKind.MESSENGER, "page"),
        channel(ChannelKind.INSTAGRAM, "page-ig"),
        channel(ChannelKind.WHATSAPP, "own", account="102030"),
        # A number under the platform's own account keeps its subscription.
        channel(ChannelKind.WHATSAPP, None),
        channel(ChannelKind.TELEGRAM, None),
    ]

    records = deprovisioner(
        channels=channels, telegram=telegram, meta=meta
    ).deprovision(BUSINESS, NOW)

    assert outcomes(records)[DeprovisionTarget.TELEGRAM_WEBHOOK] == (
        DeprovisionOutcome.DONE,
        1,
    )
    assert outcomes(records)[DeprovisionTarget.META_SUBSCRIPTION] == (
        DeprovisionOutcome.DONE,
        3,
    )
    assert telegram.removed == ["bot"]
    assert sorted(meta.pages) == ["page", "page-ig"]
    assert meta.accounts == ["102030"]


def test_an_unreachable_bot_or_unreadable_credential_is_skipped() -> None:
    channels = [
        channel(ChannelKind.TELEGRAM, "bot"),
        channel(ChannelKind.MESSENGER, UNREADABLE),
    ]

    records = deprovisioner(
        channels=channels, telegram=Telegram(failing=True)
    ).deprovision(BUSINESS, NOW)

    assert outcomes(records)[DeprovisionTarget.TELEGRAM_WEBHOOK] == (
        DeprovisionOutcome.SKIPPED,
        0,
    )
    assert outcomes(records)[DeprovisionTarget.META_SUBSCRIPTION] == (
        DeprovisionOutcome.SKIPPED,
        0,
    )


def test_voice_agents_are_removed_or_reported_skipped() -> None:
    versions = [version("agent-a"), version("agent-a"), version(None)]

    removed = deprovisioner(versions=versions).deprovision(BUSINESS, NOW)
    kept = deprovisioner(versions=versions, voice_reachable=False).deprovision(
        BUSINESS, NOW
    )

    assert outcomes(removed)[DeprovisionTarget.VOICE_AGENT] == (
        DeprovisionOutcome.DONE,
        1,
    )
    assert outcomes(kept)[DeprovisionTarget.VOICE_AGENT] == (
        DeprovisionOutcome.SKIPPED,
        0,
    )


def test_a_rented_number_goes_back_to_the_carrier_once() -> None:
    numbers = rented(PhoneNumberStatus.ACTIVE)
    provisioner = FakePhoneNumberProvisioner()
    deprovisioning = deprovisioner(numbers=numbers, provisioner=provisioner)

    first = deprovisioning.deprovision(BUSINESS, NOW)
    again = deprovisioning.deprovision(BUSINESS, NOW)

    assert outcomes(first)[DeprovisionTarget.PHONE_NUMBER] == (
        DeprovisionOutcome.DONE,
        1,
    )
    assert outcomes(again)[DeprovisionTarget.PHONE_NUMBER] == (
        DeprovisionOutcome.NOTHING,
        0,
    )
    assert status_of(numbers) is PhoneNumberStatus.RELEASED
    assert len(provisioner.releases) == 1


def test_a_number_the_carrier_keeps_fails_the_deletion_for_a_retry() -> None:
    numbers = rented(PhoneNumberStatus.RELEASING)

    with pytest.raises(ExternalServiceError):
        deprovisioner(
            numbers=numbers,
            provisioner=FakePhoneNumberProvisioner(is_release_failing=True),
        ).deprovision(BUSINESS, NOW)

    assert status_of(numbers) is PhoneNumberStatus.RELEASING


def test_automatic_charges_stop_at_their_provider() -> None:
    gateway = Gateway()

    records = deprovisioner(
        # Stripe is behind a closed release gate in storage; None is Flitt.
        subscriptions=[charging(PaymentProvider.FLITT), charging(None)],
        gateway=gateway,
    ).deprovision(BUSINESS, NOW)

    assert outcomes(records)[DeprovisionTarget.PAYMENT_SCHEDULE] == (
        DeprovisionOutcome.DONE,
        2,
    )
    assert gateway.stopped == ["flitt:sub-0000", "flitt:sub-0000"]


def test_a_provider_that_fails_to_stop_charges_fails_the_deletion() -> None:
    with pytest.raises(ExternalServiceError):
        deprovisioner(
            subscriptions=[charging(PaymentProvider.FLITT)],
            gateway=Gateway(ExternalServiceError("Flitt is down.")),
        ).deprovision(BUSINESS, NOW)


def test_payments_not_configured_here_cannot_charge_and_are_skipped() -> None:
    records = deprovisioner(
        subscriptions=[charging(PaymentProvider.FLITT)],
        gateway=Gateway(PaymentsNotConfiguredError("No merchant.")),
    ).deprovision(BUSINESS, NOW)

    assert outcomes(records)[DeprovisionTarget.PAYMENT_SCHEDULE] == (
        DeprovisionOutcome.SKIPPED,
        0,
    )

"""
What the deletion switches off at the providers before the data goes:
money is strict (a number the carrier keeps, a charge schedule the provider
keeps, both fail the job so it retries), the rest is best effort and
reported honestly on the certificate.
"""

import json
from pathlib import Path

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.business_closures import (
    DeprovisionOutcome,
    DeprovisionTarget,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.payments import PaymentProvider
from app.schemas.constants.phone_numbers import PhoneNumberStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.business_closures import DeprovisionRecord
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.payment_errors import PaymentsNotConfiguredError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.use_cases.businesses.deletion.business_deprovisioning import (
    BusinessDeprovisioner,
)
from app.use_cases.businesses.deletion.channel_deprovisioning import (
    ChannelDeprovisioner,
)
from tests.business_closures.deprovisioning_fakes import (
    UNREADABLE,
    Channels,
    Cipher,
    DisconnectCalendar,
    Gateway,
    Lock,
    MetaSubscriptions,
    PhoneNumbers,
    Provisioner,
    RemoveVoiceAgents,
    Subscriptions,
    Telegram,
    Versions,
)
from tests.storage.document_evolution.sample_documents import sample_document

BUSINESS: BusinessId = BusinessId()
GOLDEN_NUMBER: Path = (
    Path(__file__).resolve().parents[1]
    / "storage"
    / "golden"
    / "phone_numbers"
    / "v1.json"
)
NOW: Microseconds = Microseconds(1_790_000_000_000_000)


def channel(
    kind: ChannelKind, secret: str | None, account: str | None = None
) -> ChannelDocument:
    return sample_document(
        ChannelDocument, DocumentCollectionName("channels")
    ).model_copy(
        update={
            "business_id": BUSINESS,
            "kind": kind,
            "encrypted_secret": None
            if secret is None
            else EncryptedChannelSecret(secret),
            "whatsapp_business_account_id": (
                None if account is None else WhatsAppBusinessAccountId(account)
            ),
        }
    )


def version(agent: str | None) -> AssistantVersionDocument:
    return sample_document(
        AssistantVersionDocument, DocumentCollectionName("assistant_versions")
    ).model_copy(
        update={"voice_agent_id": None if agent is None else VoiceAgentId(agent)}
    )


def rented(status: PhoneNumberStatus) -> PhoneNumberDocument:
    stored = json.loads(GOLDEN_NUMBER.read_text(encoding="utf-8"))
    return PhoneNumberDocument.model_validate_json(
        json.dumps({**stored, "business_id": str(BUSINESS), "status": status.value})
    )


def charging(provider: PaymentProvider | None) -> SubscriptionDocument:
    return sample_document(
        SubscriptionDocument, DocumentCollectionName("subscriptions")
    ).model_copy(
        update={
            "provider_reference": PaymentProviderReference("sub-0000"),
            "payment_provider": provider,
        }
    )


def deprovisioner(
    *,
    channels: list[ChannelDocument] | None = None,
    telegram: Telegram | None = None,
    meta: MetaSubscriptions | None = None,
    versions: list[AssistantVersionDocument] | None = None,
    voice_reachable: bool = True,
    numbers: PhoneNumbers | None = None,
    provisioner: Provisioner | None = None,
    subscriptions: list[SubscriptionDocument] | None = None,
    gateway: Gateway | None = None,
) -> BusinessDeprovisioner:
    stored_versions = Versions(versions or [])
    return BusinessDeprovisioner(
        channels=ChannelDeprovisioner(
            Cipher(), telegram or Telegram(), meta or MetaSubscriptions()
        ),
        channel_repo=Channels(channels or []),
        assistant_version_repo=stored_versions,
        remove_voice_agent=RemoveVoiceAgents(stored_versions, voice_reachable),
        disconnect_google_calendar=DisconnectCalendar(was_connected=False),
        phone_number_repo=numbers or PhoneNumbers(None),
        phone_number_provisioner=provisioner or Provisioner(),
        phone_line_lock=Lock(),
        subscription_repo=Subscriptions(subscriptions or []),
        payment_gateway=gateway or Gateway(),
    )


def outcomes(
    records: list[DeprovisionRecord],
) -> dict[DeprovisionTarget, tuple[DeprovisionOutcome, int]]:
    return {
        record.target: (record.outcome, int(record.item_count)) for record in records
    }


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
    assert telegram.removed == ["plain-bot"]
    assert meta.pages == ["plain-page", "plain-page-ig"]
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
    numbers, provisioner = PhoneNumbers(rented(PhoneNumberStatus.ACTIVE)), Provisioner()
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
    assert (
        numbers.held is not None and numbers.held.status is PhoneNumberStatus.RELEASED
    )
    assert len(provisioner.released) == 1


def test_a_number_the_carrier_keeps_fails_the_deletion_for_a_retry() -> None:
    numbers = PhoneNumbers(rented(PhoneNumberStatus.RELEASING))

    with pytest.raises(ExternalServiceError):
        deprovisioner(
            numbers=numbers, provisioner=Provisioner(refusing=True)
        ).deprovision(BUSINESS, NOW)

    assert (
        numbers.held is not None and numbers.held.status is PhoneNumberStatus.RELEASING
    )


def test_automatic_charges_stop_at_their_provider() -> None:
    gateway = Gateway()

    records = deprovisioner(
        subscriptions=[charging(PaymentProvider.STRIPE), charging(None)],
        gateway=gateway,
    ).deprovision(BUSINESS, NOW)

    assert outcomes(records)[DeprovisionTarget.PAYMENT_SCHEDULE] == (
        DeprovisionOutcome.DONE,
        2,
    )
    assert gateway.stopped == ["stripe:sub-0000", "flitt:sub-0000"]


def test_a_provider_that_fails_to_stop_charges_fails_the_deletion() -> None:
    with pytest.raises(ExternalServiceError):
        deprovisioner(
            subscriptions=[charging(PaymentProvider.STRIPE)],
            gateway=Gateway(ExternalServiceError("Stripe is down.")),
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

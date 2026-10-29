"""Businesses with providers to switch off, built on in-memory storage."""

import json
from pathlib import Path

from typed_time_provider import Microseconds

from app.adapters.security.secret_cipher_adapter import SecretCipherAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.assistant_repositories import AssistantVersionRepository
from app.repositories.billing_repositories import SubscriptionRepository
from app.repositories.business_repositories import ChannelRepository
from app.repositories.phone_number_repositories import PhoneNumberRepository
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
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.prefixed_id import SubscriptionId
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
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
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.business_closures.deprovisioning_fakes import (
    DisconnectCalendar,
    Gateway,
    Lock,
    MetaSubscriptions,
    RemoveVoiceAgents,
    Telegram,
)
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.phone_numbers.provisioner_fakes import FakePhoneNumberProvisioner
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
CIPHER: SecretCipherAdapter = SecretCipherAdapter(
    assemble_app_settings(E2E_ENVIRONMENT)
)
UNREADABLE: str = "unreadable"


def channel(
    kind: ChannelKind, secret: str | None, account: str | None = None
) -> ChannelDocument:
    sealed: EncryptedChannelSecret | None = (
        None
        if secret is None
        else EncryptedChannelSecret(UNREADABLE)
        if secret == UNREADABLE
        else CIPHER.encrypt(ChannelSecret(secret))
    )
    return sample_document(
        ChannelDocument, DocumentCollectionName("channels")
    ).model_copy(
        update={
            "id": ChannelId(),
            "business_id": BUSINESS,
            "kind": kind,
            "encrypted_secret": sealed,
            "whatsapp_business_account_id": (
                None if account is None else WhatsAppBusinessAccountId(account)
            ),
        }
    )


def version(agent: str | None) -> AssistantVersionDocument:
    return sample_document(
        AssistantVersionDocument, DocumentCollectionName("assistant_versions")
    ).model_copy(
        update={
            "id": AssistantVersionId(),
            "business_id": BUSINESS,
            "voice_agent_id": None if agent is None else VoiceAgentId(agent),
        }
    )


def rented(status: PhoneNumberStatus) -> PhoneNumberRepository:
    stored = json.loads(GOLDEN_NUMBER.read_text(encoding="utf-8"))
    numbers = no_numbers()
    numbers.save(
        PhoneNumberDocument.model_validate_json(
            json.dumps({**stored, "business_id": str(BUSINESS), "status": status.value})
        )
    )
    return numbers


def no_numbers() -> PhoneNumberRepository:
    return PhoneNumberRepository(InMemoryDocumentCollectionAdapter(PhoneNumberDocument))


def status_of(numbers: PhoneNumberRepository) -> PhoneNumberStatus:
    stored = json.loads(GOLDEN_NUMBER.read_text(encoding="utf-8"))
    number = numbers.get(
        BUSINESS, PhoneNumberDocument.model_validate_json(json.dumps(stored)).id
    )
    assert number is not None
    return number.status


def charging(provider: PaymentProvider | None) -> SubscriptionDocument:
    return sample_document(
        SubscriptionDocument, DocumentCollectionName("subscriptions")
    ).model_copy(
        update={
            "id": SubscriptionId(),
            "business_id": BUSINESS,
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
    numbers: PhoneNumberRepository | None = None,
    provisioner: FakePhoneNumberProvisioner | None = None,
    subscriptions: list[SubscriptionDocument] | None = None,
    gateway: Gateway | None = None,
) -> BusinessDeprovisioner:
    channel_repo = ChannelRepository(InMemoryDocumentCollectionAdapter(ChannelDocument))
    for stored_channel in channels or []:
        channel_repo.save(stored_channel)
    version_repo = AssistantVersionRepository(
        InMemoryDocumentCollectionAdapter(AssistantVersionDocument)
    )
    for stored_version in versions or []:
        version_repo.save(stored_version)
    subscription_repo = SubscriptionRepository(
        InMemoryDocumentCollectionAdapter(SubscriptionDocument)
    )
    for subscription in subscriptions or []:
        subscription_repo.save(subscription)
    return BusinessDeprovisioner(
        channels=ChannelDeprovisioner(
            CIPHER, telegram or Telegram(), meta or MetaSubscriptions()
        ),
        channel_repo=channel_repo,
        assistant_version_repo=version_repo,
        remove_voice_agent=RemoveVoiceAgents(version_repo, voice_reachable),
        disconnect_google_calendar=DisconnectCalendar(was_connected=False),
        phone_number_repo=numbers or no_numbers(),
        phone_number_provisioner=provisioner or FakePhoneNumberProvisioner(),
        phone_line_lock=Lock(),
        subscription_repo=subscription_repo,
        payment_gateway=gateway or Gateway(),
    )


def outcomes(
    records: list[DeprovisionRecord],
) -> dict[DeprovisionTarget, tuple[DeprovisionOutcome, int]]:
    return {
        record.target: (record.outcome, int(record.item_count)) for record in records
    }

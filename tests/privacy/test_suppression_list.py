"""
The suppression list keeps only keyed digests: an entry matches the
identity it was made from (a number in any spelling, one account of one
channel) in one business, reveals nothing of it and survives erasure.
"""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.privacy_repositories import SuppressionEntryRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.suppression import SuppressionEntryDocument
from app.schemas.dto.privacy.suppression import SuppressedIdentity
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.constrained_integers import SuppressedIdentityCount
from app.schemas.typings.privacy.strings import SuppressedIdentityText
from app.utilities.privacy.suppressed_identities import (
    channel_identity,
    contact_identities,
    phone_identity,
)
from app.utilities.privacy.suppression_digests import (
    derive_suppression_key,
    suppression_digest,
    suppression_entry_id,
)
from tests.compliance.two_tenants import command, seed_two_tenants
from tests.privacy.suppression_doubles import (
    TEST_SUPPRESSION_KEY,
    build_suppression_list,
)

BUSINESS: BusinessId = BusinessId()
OTHER_BUSINESS: BusinessId = BusinessId()
NUMBER: E164PhoneNumber = E164PhoneNumber("+995599123456")


def test_suppressing_is_idempotent_and_lifting_removes_the_entry() -> None:
    entries = SuppressionEntryRepository(
        InMemoryDocumentCollectionAdapter(SuppressionEntryDocument)
    )
    suppression_list = build_suppression_list(entries)
    identity = phone_identity(NUMBER)

    first = suppression_list.suppress(BUSINESS, [identity, identity], Microseconds(1))
    again = suppression_list.suppress(BUSINESS, [identity], Microseconds(2))

    assert first == SuppressedIdentityCount(1)
    assert again == SuppressedIdentityCount(0)
    assert suppression_list.is_suppressed(BUSINESS, [identity]) is True
    assert suppression_list.is_suppressed(OTHER_BUSINESS, [identity]) is False
    assert suppression_list.is_suppressed(BUSINESS, []) is False

    assert suppression_list.lift(BUSINESS, [identity]) == SuppressedIdentityCount(1)
    assert suppression_list.is_suppressed(BUSINESS, [identity]) is False


def test_a_number_matches_in_any_spelling_and_the_entry_hides_it() -> None:
    entries = SuppressionEntryRepository(
        InMemoryDocumentCollectionAdapter(SuppressionEntryDocument)
    )
    suppression_list = build_suppression_list(entries)
    suppression_list.suppress(BUSINESS, [phone_identity(NUMBER)], Microseconds(1))

    spelled = SuppressedIdentity(
        channel=ChannelKind.PHONE, value=SuppressedIdentityText("995 599 12-34-56")
    )
    assert suppression_list.is_suppressed(BUSINESS, [spelled]) is True
    whatsapp = channel_identity(ChannelKind.WHATSAPP, ChannelUserId("995599123456"))
    assert suppression_list.is_suppressed(BUSINESS, [whatsapp]) is False

    key = derive_suppression_key(TEST_SUPPRESSION_KEY, None)
    digest = suppression_digest(key, BUSINESS, phone_identity(NUMBER))
    stored = entries.get_many(BUSINESS, [suppression_entry_id(BUSINESS, digest)])
    assert len(stored) == 1
    serialized = stored[0].model_dump_json()
    assert "599123456" not in serialized
    assert stored[0].channel is ChannelKind.PHONE


def test_digests_depend_on_the_key_and_the_business() -> None:
    identity = phone_identity(NUMBER)
    configured = derive_suppression_key(PlatformSecret("key-a-0000"), None)
    from_encryption = derive_suppression_key(None, PlatformSecret("key-a-0000"))
    development = derive_suppression_key(None, None)

    assert derive_suppression_key(None, None) == development
    assert len({configured, development}) == 2
    assert configured == from_encryption  # one derivation, two sources
    digest = suppression_digest(configured, BUSINESS, identity)
    assert len(str(digest)) == 64
    assert digest != suppression_digest(configured, OTHER_BUSINESS, identity)
    assert digest != suppression_digest(development, BUSINESS, identity)


def test_a_contact_is_listed_by_its_numbers_and_accounts() -> None:
    contact = ContactDocument(
        business_id=BUSINESS,
        phone_number=NUMBER,
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.WHATSAPP,
                channel_user_id=ChannelUserId("995599123456"),
            ),
            ChannelIdentity(
                channel=ChannelKind.OWNER_TEST, channel_user_id=ChannelUserId("me")
            ),
        ],
    )

    assert contact_identities(contact) == [
        phone_identity(NUMBER),
        channel_identity(ChannelKind.WHATSAPP, ChannelUserId("995599123456")),
    ]
    assert contact_identities(None) == []


def test_erasure_carries_an_earlier_stop_over_to_the_list() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed
    contact = tenants.visitor.contact.model_copy(
        update={"opted_out_channels": [ChannelKind.TELEGRAM]}
    )
    testbed.contact_repo.save(contact)

    testbed.delete_contact_data.run(command(tenants, contact.id))

    business_id = tenants.business.id
    telegram = channel_identity(ChannelKind.TELEGRAM, ChannelUserId("4242"))
    assert testbed.suppression_list.is_suppressed(business_id, [telegram]) is True
    number = phone_identity(E164PhoneNumber("+995577123456"))
    assert testbed.suppression_list.is_suppressed(business_id, [number]) is True
    neighbour = channel_identity(ChannelKind.TELEGRAM, ChannelUserId("5353"))
    assert testbed.suppression_list.is_suppressed(business_id, [neighbour]) is False


def test_erasure_without_a_stop_lists_nobody() -> None:
    tenants = seed_two_tenants()
    testbed = tenants.testbed

    testbed.delete_contact_data.run(command(tenants, tenants.visitor.contact.id))

    telegram = channel_identity(ChannelKind.TELEGRAM, ChannelUserId("4242"))
    assert (
        testbed.suppression_list.is_suppressed(tenants.business.id, [telegram]) is False
    )

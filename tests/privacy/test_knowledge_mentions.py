"""How a knowledge item is found to name a customer (PRIV-08)."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.privacy import KnowledgeMentionMatch
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.knowledge import KnowledgeAttribute, KnowledgeItemDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAttributeKey
from app.schemas.typings.knowledge.strings import (
    KnowledgeAttributeValue,
    KnowledgeBody,
    KnowledgeTitle,
)
from app.utilities.privacy.knowledge_mentions import mention_matches

BUSINESS: BusinessId = BusinessId()


def item(
    title: str, body: str | None = None, note: str | None = None
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=BUSINESS,
        kind=KnowledgeItemKind.FAQ,
        title=KnowledgeTitle(title),
        body=None if body is None else KnowledgeBody(body),
        attributes=(
            []
            if note is None
            else [
                KnowledgeAttribute(
                    key=KnowledgeAttributeKey("note"),
                    value=KnowledgeAttributeValue(note),
                )
            ]
        ),
    )


def test_a_whatsapp_number_in_an_attribute_names_the_customer() -> None:
    customer = ContactDocument(
        business_id=BUSINESS,
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.WHATSAPP,
                channel_user_id=ChannelUserId("393331234567"),
            )
        ],
    )

    found = mention_matches(item("Regulars", note="+39 333 123 4567"), customer)

    assert found == [KnowledgeMentionMatch.PHONE]


def test_a_name_of_two_letters_names_nobody() -> None:
    customer = ContactDocument(business_id=BUSINESS, name=ContactName("Al"))

    assert mention_matches(item("Al fresco dining"), customer) == []


def test_a_customer_without_name_or_number_is_named_by_no_item() -> None:
    customer = ContactDocument(business_id=BUSINESS)

    assert mention_matches(item("Anyone", "+39 333 123 4567"), customer) == []

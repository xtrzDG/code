"""
The team's card on a customer (tags, VIP, block): how a plain save keeps
it, and the tag rules every writer shares.
"""

from typed_time_provider import Microseconds

from app.schemas.domain.contacts import ContactDocument, ContactTagMark
from app.schemas.typings.contacts.constrained_strings import (
    CustomerTag,
    CustomerTagKey,
)
from app.schemas.typings.users.prefixed_id import UserId

# Tags one customer carries at most, and tags the business's list keeps.
MAX_TAGS_PER_CUSTOMER: int = 20
MAX_KNOWN_TAGS: int = 100


def keep_card_fields(
    incoming: ContactDocument, stored: ContactDocument
) -> ContactDocument:
    """
    The contact to store for a plain save: the incoming one with the card
    as stored (a turn that read the contact before a colleague tagged or
    blocked it must not undo that). An erasure stores no card.
    """

    if incoming.erased_at is not None:
        return incoming

    return incoming.model_copy(
        update={
            "tags": list(stored.tags),
            "is_vip": stored.is_vip,
            "block": stored.block,
            "is_blocked": stored.block is not None,
        }
    )


def tag_key(tag: CustomerTag) -> CustomerTagKey:
    """Tags compare without case ("VIP" is "vip"): the tag's folded key."""

    return CustomerTagKey(str(tag).casefold())


def add_tags(
    contact: ContactDocument,
    tags: list[CustomerTag],
    actor_id: UserId,
    now: Microseconds,
) -> list[CustomerTag]:
    """
    Put the tags on the contact (a tag it has in another case is kept as
    it is); returns the ones actually added. At most MAX_TAGS_PER_CUSTOMER.
    """

    present: set[CustomerTagKey] = {mark.key for mark in contact.tags}
    added: list[CustomerTag] = []
    for tag in tags:
        key: CustomerTagKey = tag_key(tag)
        if key in present or len(contact.tags) >= MAX_TAGS_PER_CUSTOMER:
            continue

        contact.tags.append(
            ContactTagMark(tag=tag, key=key, added_at=now, added_by=actor_id)
        )
        present.add(key)
        added.append(tag)

    return added


def remove_tags(contact: ContactDocument, tags: list[CustomerTag]) -> None:
    """Take the tags off the contact, in any case."""

    removed: set[CustomerTagKey] = {tag_key(tag) for tag in tags}
    contact.tags = [mark for mark in contact.tags if mark.key not in removed]


def remember_tags(
    known: list[CustomerTag], used: list[CustomerTag]
) -> list[CustomerTag]:
    """The business's tags with the newly used ones first, at most MAX_KNOWN_TAGS."""

    used_keys: set[CustomerTagKey] = {tag_key(tag) for tag in used}
    return [
        *used,
        *(tag for tag in known if tag_key(tag) not in used_keys),
    ][:MAX_KNOWN_TAGS]


def tag_values(contact: ContactDocument) -> list[CustomerTag]:
    return [mark.tag for mark in contact.tags]

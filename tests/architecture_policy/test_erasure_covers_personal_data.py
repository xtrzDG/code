"""
Every stored collection that can hold a customer's number, e-mail, channel
account or words is either handled by the erasure of a customer's data
(`DeleteContactDataUseCase` takes its repository, and so finds and erases
the customer's rows) or listed below with the reason it holds no customer's
personal data. A new collection with such a field fails here until one of
the two is true.
"""

import inspect
import types
import typing

from pydantic import BaseModel

from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.compliance.delete_contact_data_use_case import (
    DeleteContactDataUseCase,
)
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS

PERSONAL_TYPES: tuple[type, ...] = (
    E164PhoneNumber,
    EmailAddress,
    ChannelUserId,
    MessageText,
)

# Collection -> the erasure's parameter whose repository erases its rows.
ERASED_BY: dict[str, str] = {
    "contacts": "contact_repo",
    "conversations": "conversation_repo",
    "messages": "message_repo",
    "calls": "call_repo",
    "missed_calls": "missed_call_repo",
    "outbound_messages": "outbound_message_repo",
    "inbound_events": "inbound_event_repo",
}

# Collections whose personal fields belong to no customer of a business.
NOT_CUSTOMER_DATA: dict[str, str] = {
    "users": "cabinet users (owners, staff); their account, not a customer's",
    "otp_challenges": "sign-in codes of cabinet users, purged after 24 hours",
    "business_profiles": "the business's own public phone number",
    "autotest_runs": (
        "the scripted test customer's messages of an autotest: written by "
        "the model, no real person"
    ),
    "digest_preferences": "the owner's own number for digests and reports",
    "platform_admins": "the platform's own team",
    "billing_profiles": "the business's own details for its invoices (1114)",
    "invoices": (
        "the business and the platform as the parties of an invoice, copied "
        "from the billing details when it is issued (1114)"
    ),
}


def personal_types_of(annotation: object, seen: set[type]) -> set[str]:
    """The personal primitives a field type holds, in nested documents too."""

    found: set[str] = set()
    arguments = typing.get_args(annotation)
    if typing.get_origin(annotation) is not None or isinstance(
        annotation, types.UnionType
    ):
        for argument in arguments:
            found |= personal_types_of(argument, seen)
        return found

    if not isinstance(annotation, type):
        return found

    found |= {
        personal.__name__
        for personal in PERSONAL_TYPES
        if issubclass(annotation, personal)
    }
    if issubclass(annotation, BaseModel) and annotation not in seen:
        seen.add(annotation)
        for field in annotation.model_fields.values():
            found |= personal_types_of(field.annotation, seen)

    return found


def collections_with_personal_data() -> dict[str, set[str]]:
    return {
        str(definition.name): fields
        for definition in DOCUMENT_COLLECTIONS
        if (fields := personal_types_of(definition.document_type, set()))
    }


def test_every_collection_with_personal_fields_is_erased_or_explained() -> None:
    unhandled = {
        name: sorted(fields)
        for name, fields in collections_with_personal_data().items()
        if name not in ERASED_BY and name not in NOT_CUSTOMER_DATA
    }

    assert unhandled == {}, (
        "Erase these collections in DeleteContactDataUseCase, or explain in "
        "NOT_CUSTOMER_DATA why they hold no customer's personal data: "
        f"{unhandled}"
    )


def test_the_erasure_takes_the_repository_of_every_erased_collection() -> None:
    parameters = inspect.signature(DeleteContactDataUseCase.__init__).parameters

    assert [
        repository for repository in ERASED_BY.values() if repository not in parameters
    ] == []


def test_the_tables_name_only_collections_with_personal_fields() -> None:
    personal = collections_with_personal_data()

    assert set(ERASED_BY).isdisjoint(NOT_CUSTOMER_DATA)
    assert [
        name for name in [*ERASED_BY, *NOT_CUSTOMER_DATA] if name not in personal
    ] == []


def test_the_scan_sees_through_optional_lists_and_nested_documents() -> None:
    class Inner(BaseModel):
        sender: ChannelUserId

    class Outer(BaseModel):
        inner: list[Inner] | None = None
        phone: E164PhoneNumber | None = None

    assert personal_types_of(Outer, set()) == {"ChannelUserId", "E164PhoneNumber"}

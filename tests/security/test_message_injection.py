"""
Names typed by owners and customers never act as a template or a header
(ASVS V1.3.7, V1.3.10, V1.3.11). Platform texts are code constants filled
once with `str.format`, so a business name holding template syntax lands
in the message as typed; a staff e-mail's subject is one header line, so
a customer's name with CR, LF or other breaks cannot add a Bcc.
"""

import email
from email import policy

import pytest

from app.schemas.constants.bookings import BookingConfirmationChange, BookingUnit
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.profiles import BusinessAddress
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import BookingManageLink
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.strings import AddressText, BusinessName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.bookings.confirmations.confirmation_message import (
    ConfirmationFacts,
    ConfirmationWriter,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.notifications.staff_email import build_staff_email
from tests.foundation.builders import build_business
from tests.users.test_smtp_email_client import (
    RECIPIENT,
    Connections,
    FakeSmtp,
    build_client,
)

TEMPLATE_PAYLOADS: tuple[str, ...] = (
    "{0.__class__.__mro__}",
    "{business.__init__.__globals__}",
    "{{ ''.__class__.__mro__[1].__subclasses__() }}",
    "{% for x in range(9) %}{{x}}{% endfor %}",
    "${7*7}",
    "%(when)s",
    "{when}",
)
HEADER_PAYLOADS: tuple[str, ...] = (
    "Anna\r\nBcc: spam@example.com",
    "Anna\rBcc: spam@example.com",
    "Anna\x0bBcc: spam@example.com",
    "Anna\x85Bcc: spam@example.com",
    "Anna Bcc: spam@example.com",
    "Anna Bcc: spam@example.com",
    "Anna\x00\r\nX-Injected: 1",
)


def confirmation(business_name: str, service: str) -> ConfirmationFacts:
    business = build_business(UserId()).model_copy(
        update={"name": BusinessName(business_name)}
    )
    booking = BookingDocument(
        business_id=business.id,
        resource_id=ResourceId(),
        contact_id=ContactId(),
        starts_at=BookingStartsAtUnixSeconds(1_790_100_000),
        ends_at=BookingEndsAtUnixSeconds(1_790_107_200),
        party_size=PartySize(2),
        source_channel=ChannelKind.WHATSAPP,
    )
    return ConfirmationFacts(
        business=business,
        booking=booking,
        booking_unit=BookingUnit.TIME_SLOT,
        service_title=KnowledgeTitle(service),
        address=BusinessAddress(text=AddressText(f"Via Roma 1 {service}")),
        manage_link=BookingManageLink("https://app.workshop.example/r/AAAA"),
        change=BookingConfirmationChange.BOOKED,
        language=LanguageTag("it"),
    )


@pytest.mark.parametrize("payload", TEMPLATE_PAYLOADS)
def test_template_syntax_in_names_is_sent_as_typed(payload: str) -> None:
    writer = ConfirmationWriter(LocalizedTextResolver())
    facts = confirmation(f"Trattoria {payload}", payload)

    text = str(writer.text(facts))
    parameters = writer.template_parameters(facts)

    assert f"Trattoria {payload}" in text
    assert f"Via Roma 1 {payload}" in text
    assert text.count(payload) == 3
    assert "<class" not in text and "49" not in text
    assert parameters is not None
    assert str(parameters[0]) == f"Trattoria {payload}"


@pytest.mark.parametrize("payload", HEADER_PAYLOADS)
def test_a_name_with_line_breaks_adds_no_header_to_a_staff_email(
    payload: str,
) -> None:
    staff_email = build_staff_email(
        MessageText(f"New booking: {payload}\nTrattoria Milano · 2 guests")
    )
    connections = Connections(FakeSmtp())

    build_client(connections).send_email(
        recipient=RECIPIENT,
        subject=staff_email.subject,
        text_body=staff_email.text_body,
        html_body=staff_email.html_body,
    )

    [sent] = connections.smtp.sent
    parsed = email.message_from_bytes(sent.as_bytes(), policy=policy.default)
    header_names = [name.lower() for name in parsed]
    assert "bcc" not in header_names
    assert "x-injected" not in header_names
    assert header_names.count("subject") == 1
    subject = str(parsed["Subject"])
    assert subject.startswith("New booking: Anna")
    assert not any(character in subject for character in "\r\n\x0b\x85  ")


def test_a_subject_of_control_characters_only_falls_back_to_the_footer() -> None:
    assert str(build_staff_email(MessageText("\x00\x0b\nBody")).subject) == (
        "Assistant Workshop"
    )

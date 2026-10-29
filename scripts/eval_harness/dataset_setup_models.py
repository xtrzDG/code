"""
What a dataset scenario prepares before its conversation (`channel`,
`setup`, `attachment` of evals/datasets/<niche>.yaml).

A scenario played on WhatsApp is a real customer conversation, not the
owner's test chat: the persona writes from their own number, which the
channel proves, so their bookings and the customer memory are theirs. Its
`setup` seeds what that customer already has with the business: a booking
still to come (made with the product's own create-booking use case), an
earlier conversation the memory recalls (its summary, the team's note on
it, an order the team has not closed yet), and for an attack another
customer whose details must stay private. `attachment` makes the first
message a voice note (its text is the transcript) or sends a photo with it.
"""

from enum import StrEnum

from pydantic import Field

from scripts.eval_harness.strict_model import StrictModel


class ScenarioChannel(StrEnum):
    """Where the persona writes from."""

    # The owner's test chat: a sandbox conversation, nothing is remembered.
    OWNER_TEST = "owner_test"
    # A real customer on WhatsApp: the channel proves the persona's phone.
    WHATSAPP = "whatsapp"


class BookingSeedSpec(StrictModel):
    """
    A booking made before the conversation, with create_booking's fields
    (a local date, the time or the nights of a stay, the party).
    """

    date: str
    time: str | None = None
    party_size: int
    nights: int | None = None
    duration_minutes: int | None = None


class EarlierConversationSpec(StrictModel):
    """
    An earlier conversation of the persona that the customer memory
    recalls: its summary, the team's internal note on it (shared with the
    assistant, never to be quoted) and an order or request from it the
    team has not closed yet (`lead`, its details).
    """

    summary: str
    days_ago: int = Field(default=12, ge=1)
    note: str | None = None
    lead: str | None = None


class OtherCustomerSpec(StrictModel):
    """Another customer of the business and their booking: what an attacker wants."""

    name: str
    phone: str
    booking: BookingSeedSpec | None = None


class SetupSpec(StrictModel):
    """What the persona (and the business) already has before the conversation."""

    booking: BookingSeedSpec | None = None
    earlier: EarlierConversationSpec | None = None
    other_customer: OtherCustomerSpec | None = None


class AttachmentSpec(StrictModel):
    """
    What the first customer message carries: a voice note whose transcript
    is the message (`voice_note`), or a photo from evals/media (`photo`).
    """

    voice_note: bool = False
    photo: str | None = None

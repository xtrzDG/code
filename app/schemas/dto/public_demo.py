"""
The landing page's sandbox demos: demo businesses a visitor chats with
before signing up (PUBLIC_DEMO_BUSINESS_IDS). Every turn runs in sandbox:
bookings and requests are test records, no staff is alerted and nothing is
billed.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.niches import NicheKey
from app.schemas.dto.channels.widget import WidgetStarterQuestionView
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.public_site.booleans import (
    IsDemoBookingMade,
    IsDemoHandoffMade,
    IsDemoRequestMade,
)
from app.schemas.typings.public_site.constrained_integers import (
    PublicDemoMessagesLeft,
)
from app.schemas.typings.public_site.constrained_strings import (
    PublicDemoMessageText,
    PublicDemoSessionKey,
)


class PublicDemoListQuery(ImmutableDTO):
    """GET /v1/public-demos: the demos, their niches named in `language`."""

    language: LanguageTag


class PublicDemoBusinessIds(ImmutableDTO):
    """The demo businesses, in the order the landing page offers them."""

    business_ids: list[BusinessId]


class PublicDemoCardQuery(ImmutableDTO):
    """One demo business described for the landing page."""

    business_id: BusinessId
    language: LanguageTag


class PublicDemoCard(ImmutableDTO):
    """
    A demo business a visitor can chat with: its name, kind of business
    (`niche_name` in the language asked for), city and country, the
    languages its assistant answers in, and up to three starter questions
    per language from its FAQ.
    """

    business_id: BusinessId
    business_name: BusinessName
    niche_key: NicheKey
    niche_name: LocalizedTextValue
    city: CityName | None = None
    country_code: CountryCode
    default_language: LanguageTag
    languages: list[LanguageTag]
    starters: list[WidgetStarterQuestionView] = Field(
        default_factory=list[WidgetStarterQuestionView]
    )


class PublicDemoList(ImmutableDTO):
    """
    Every demo that can answer now (a configured business without a
    published assistant is left out), and how many messages one visitor
    may send each demo in an hour.
    """

    demos: list[PublicDemoCard]
    messages_per_hour: PublicDemoMessagesLeft


class PublicDemoMessageRequest(ImmutableDTO):
    """
    HTTP body of a visitor's message to a demo: the text and the key of the
    visitor's conversation (random, chosen by the page).
    """

    text: PublicDemoMessageText
    session_key: PublicDemoSessionKey


class PublicDemoMessageCommand(ImmutableDTO):
    """A visitor's message to one demo business, with the caller's address."""

    business_id: BusinessId
    request: PublicDemoMessageRequest
    client_ip_address: ClientIpAddress | None = None


class PublicDemoTurnOutcome(ImmutableDTO):
    """A demo turn's reply, to be told to the visitor."""

    business_id: BusinessId
    reply: AssistantReply


class PublicDemoReply(ImmutableDTO):
    """
    The demo assistant's answer and what the turn did, all in sandbox: a
    booking, a request taken down or a handoff to a person happen only as
    test records. `messages_left`: how many more messages this visitor may
    send this demo in the current hour.
    """

    text: MessageText | None
    language: LanguageTag
    is_booking_made: IsDemoBookingMade = False
    is_request_made: IsDemoRequestMade = False
    is_handoff_made: IsDemoHandoffMade = False
    messages_left: PublicDemoMessagesLeft

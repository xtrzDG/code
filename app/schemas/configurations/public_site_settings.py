from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.public_site.booleans import AreLegalTextsFinal
from app.schemas.typings.public_site.constrained_integers import (
    PublicDemoMessagesPerHour,
)

DEFAULT_PUBLIC_DEMO_MESSAGES_PER_HOUR: int = 300


class PublicSiteSettings(ImmutableDTO):
    """
    The public site around the cabinet: the demo businesses visitors of the
    landing page may chat with (PUBLIC_DEMO_BUSINESS_IDS, in sandbox: no
    real bookings, no staff alerts, no billing), how many demo messages
    every visitor together may send in an hour
    (PUBLIC_DEMO_MESSAGES_PER_HOUR), and whether the legal texts are final
    (LEGAL_TEXTS_FINAL; until then the public pages say they are drafts).
    """

    demo_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
    demo_messages_per_hour: PublicDemoMessagesPerHour = PublicDemoMessagesPerHour(
        DEFAULT_PUBLIC_DEMO_MESSAGES_PER_HOUR
    )
    are_legal_texts_final: AreLegalTextsFinal = False

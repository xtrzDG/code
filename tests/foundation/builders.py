"""Small builders of valid documents shared by foundation tests."""

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.prefixed_id import UserId


def build_business(
    owner_id: UserId,
    staff_ids: list[UserId] | None = None,
) -> BusinessDocument:
    members: list[BusinessMember] = [
        BusinessMember(user_id=owner_id, role=BusinessMemberRole.OWNER)
    ]
    for staff_id in staff_ids or []:
        members.append(BusinessMember(user_id=staff_id, role=BusinessMemberRole.STAFF))

    return BusinessDocument(
        name=BusinessName("Trattoria Milano"),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode("IT"),
        timezone=TimezoneName("Europe/Rome"),
        currency_code=CurrencyCode("EUR"),
        languages=[LanguageTag("it"), LanguageTag("en")],
        default_language=LanguageTag("it"),
        owner_language=LanguageTag("it"),
        plan_key=PlanKey.VOICE_AND_CHAT,
        data_region=DataRegion.EU,
        members=members,
    )

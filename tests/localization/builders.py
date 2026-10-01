"""Shared builders for localization tests: fixed clocks, registries, businesses."""

from functools import cache

from typed_time_provider import Microseconds, WallClock

from app.registries.localization.country_registry import CountryRegistry
from app.registries.localization.language_registry import LanguageRegistry
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

# 2026-10-01 09:00 UTC, the concept's date.
OCTOBER_2026_NANOSECONDS: int = 1_790_845_200_000_000_000
# 2026-07-15 12:00 UTC (northern summer time).
JULY_2026_NANOSECONDS: int = 1_784_116_800_000_000_000
# 2026-01-15 12:00 UTC (northern winter time).
JANUARY_2026_NANOSECONDS: int = 1_768_478_400_000_000_000
# 2025-06-01 00:00 UTC, before Bulgaria's euro changeover.
JUNE_2025_NANOSECONDS: int = 1_748_736_000_000_000_000
RESTRICTED_COUNTRY_CODES: list[CountryCode] = [
    CountryCode("CU"),
    CountryCode("IR"),
    CountryCode("KP"),
    CountryCode("SY"),
]


def build_wall_clock(
    unix_nanoseconds: int = OCTOBER_2026_NANOSECONDS,
) -> WallClock[Microseconds]:
    return WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: unix_nanoseconds,
    )


@cache
def get_language_registry() -> LanguageRegistry:
    """One registry for the whole test session (profiles are cached)."""

    return LanguageRegistry()


@cache
def get_country_registry() -> CountryRegistry:
    """Country registry as wired in production: EU data, sanctioned countries."""

    return CountryRegistry(
        language_registry=get_language_registry(),
        wall_clock=build_wall_clock(),
        default_data_region=DataRegion.EU,
        restricted_country_codes=RESTRICTED_COUNTRY_CODES,
    )


def build_business(
    owner_id: UserId,
    country_code: str,
    owner_language: str,
    staff_ids: list[UserId] | None = None,
) -> BusinessDocument:
    """A business of any country; time zone and currency are not used here."""

    members: list[BusinessMember] = [
        BusinessMember(user_id=owner_id, role=BusinessMemberRole.OWNER)
    ]
    for staff_id in staff_ids or []:
        members.append(BusinessMember(user_id=staff_id, role=BusinessMemberRole.STAFF))

    return BusinessDocument(
        name=BusinessName("VR Arena"),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode(country_code),
        timezone=TimezoneName("Asia/Tbilisi"),
        currency_code=CurrencyCode("GEL"),
        languages=[LanguageTag(owner_language), LanguageTag("en")],
        default_language=LanguageTag(owner_language),
        owner_language=LanguageTag(owner_language),
        plan_key=PlanKey.VOICE_AND_CHAT,
        data_region=DataRegion.EU,
        members=members,
    )

"""How a business's value is estimated: the average check and the staff time rates."""

from dataclasses import dataclass

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    ScheduleExceptionRepoContract,
)
from app.contracts.repositories.value_repositories import ValueSettingsRepoContract
from app.contracts.value import NicheValueRegistryContract
from app.schemas.constants.value import AverageCheckSource, ValueBasis
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.value_settings import ValueSettingsDocument
from app.schemas.dto.value.niche_value import NicheValueDefaults
from app.schemas.typings.value.constrained_integers import AverageCheckMinor
from app.use_cases.insights.value.value_counting import ValueRates
from app.utilities.scheduling.opening_hours import DayRanges, business_day_ranges
from app.utilities.value.typical_check import typical_check_in


@dataclass(frozen=True)
class ValueEstimates:
    """The rates of a business and where its average check came from."""

    rates: ValueRates
    source: AverageCheckSource
    typical_check: AverageCheckMinor | None


@dataclass(frozen=True)
class EstimateCatalogs:
    """The catalogs and settings an estimate is read from."""

    niche_value_registry: NicheValueRegistryContract
    niche_template_registry: NicheTemplateRegistryContract
    exchange_rate_registry: ExchangeRateRegistryContract
    value_settings_repo: ValueSettingsRepoContract


def estimate_business_value(
    catalogs: EstimateCatalogs,
    business: BusinessDocument,
) -> ValueEstimates:
    """
    The owner's average check when they set one, else the niche's typical
    check in the business currency (official rate), else none. Niches that
    take orders instead of bookings earn by their requests.
    """

    defaults: NicheValueDefaults = catalogs.niche_value_registry.get(business.niche_key)
    typical: AverageCheckMinor | None = typical_check_in(
        defaults.typical_check,
        business.currency_code,
        None
        if defaults.typical_check is None
        else catalogs.exchange_rate_registry.find_rate(
            defaults.typical_check.currency_code, business.currency_code
        ),
    )
    settings: ValueSettingsDocument | None = (
        catalogs.value_settings_repo.get_by_business(business.id)
    )
    owner_check: AverageCheckMinor | None = (
        None if settings is None else settings.average_check_minor
    )
    source: AverageCheckSource = (
        AverageCheckSource.OWNER
        if owner_check is not None
        else (
            AverageCheckSource.NONE
            if typical is None
            else AverageCheckSource.NICHE_DEFAULT
        )
    )
    takes_bookings: bool = catalogs.niche_template_registry.get(
        business.niche_key
    ).takes_bookings
    return ValueEstimates(
        rates=ValueRates(
            basis=ValueBasis.BOOKINGS if takes_bookings else ValueBasis.REQUESTS,
            average_check=owner_check if owner_check is not None else typical,
            seconds_per_reply=defaults.seconds_per_reply,
            seconds_per_call=defaults.seconds_per_call,
        ),
        source=source,
        typical_check=typical,
    )


def read_weekly_hours(
    business_profile_repo: BusinessProfileRepoContract,
    schedule_exception_repo: ScheduleExceptionRepoContract,
    business: BusinessDocument,
) -> DayRanges | None:
    """The business's opening ranges by date; None without weekly hours."""

    profile: BusinessProfileDocument | None = business_profile_repo.get_by_business(
        business.id
    )
    if profile is None or not profile.hours:
        return None

    return business_day_ranges(
        list(profile.hours),
        schedule_exception_repo.list_by_business(business.id),
    )

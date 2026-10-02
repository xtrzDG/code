"""Building blocks for seeded businesses: hours, a launch-ready business, menu items."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import BillingPeriod, PlanKey, SubscriptionStatus
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import (
    BusinessDocument,
    BusinessMember,
    ManagerContact,
)
from app.schemas.domain.compliance import DpaAcceptanceDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import (
    OpeningInterval,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes
from app.schemas.typings.knowledge.constrained_strings import (
    KnowledgeTag,
)
from app.schemas.typings.knowledge.strings import (
    KnowledgeBody,
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from tests.assembly.testbed import AssemblyTestbed


def interval(weekday: Weekday, opens: str, closes: str) -> OpeningInterval:
    """Interval from "HH:MM" texts; "24:00" closes at midnight."""

    open_hours, open_minutes = (int(part) for part in opens.split(":"))
    close_hours, close_minutes = (int(part) for part in closes.split(":"))
    return OpeningInterval(
        weekday=weekday,
        opens_at=OpeningMinuteOfDay(open_hours * 60 + open_minutes),
        closes_at=ClosingMinuteOfDay(close_hours * 60 + close_minutes),
    )


TRIAL_SECONDS: int = 14 * 24 * 60 * 60


def build_business(
    testbed: AssemblyTestbed,
    *,
    name: str,
    niche_key: NicheKey,
    country_code: str,
    city: str | None,
    timezone_name: str,
    currency_code: str,
    languages: list[str],
    plan_key: PlanKey = PlanKey.CHAT,
    is_launch_ready: bool = True,
) -> BusinessDocument:
    """
    A business with its owner and a staff member. A launch-ready one also
    has a manager contact, a running trial and the current DPA accepted,
    so only its profile and versions decide whether it may go live.
    """

    business = BusinessDocument(
        name=BusinessName(name),
        niche_key=niche_key,
        country_code=CountryCode(country_code),
        city=CityName(city) if city is not None else None,
        timezone=TimezoneName(timezone_name),
        currency_code=CurrencyCode(currency_code),
        languages=[LanguageTag(tag) for tag in languages],
        default_language=LanguageTag(languages[0]),
        owner_language=LanguageTag(languages[0]),
        plan_key=plan_key,
        data_region=DataRegion.EU,
        members=[
            BusinessMember(user_id=testbed.owner_id, role=BusinessMemberRole.OWNER),
            BusinessMember(user_id=testbed.staff_id, role=BusinessMemberRole.STAFF),
        ],
    )
    testbed.business_repo.save(business)
    if is_launch_ready:
        make_launch_ready(testbed, business)

    return business


def make_launch_ready(testbed: AssemblyTestbed, business: BusinessDocument) -> None:
    """A manager contact, a running trial and the current DPA accepted."""

    now = testbed.wall_clock.now_unix()
    business.manager_contacts = [
        ManagerContact(
            name=ManagerName("Nino"),
            channel=ManagerContactChannel.TELEGRAM,
            address=ManagerContactAddress("70001"),
            language=business.owner_language,
        )
    ]
    testbed.business_repo.save(business)
    testbed.subscription_repo.save(
        SubscriptionDocument(
            business_id=business.id,
            plan_key=business.plan_key,
            billing_period=BillingPeriod.MONTHLY,
            price_minor=MoneyAmountMinor(0),
            currency_code=business.currency_code,
            status=SubscriptionStatus.TRIALING,
            trial_ends_at=Microseconds(int(now) + TRIAL_SECONDS * 1_000_000),
            period_start=now,
            period_end=Microseconds(int(now) + TRIAL_SECONDS * 1_000_000),
            created_at=now,
            updated_at=now,
        )
    )
    testbed.dpa_repo.save(
        DpaAcceptanceDocument(
            business_id=business.id,
            document_version=testbed.settings.dpa_document_version,
            accepted_by=testbed.owner_id,
            accepted_at=now,
            created_at=now,
            updated_at=now,
        )
    )


def build_menu_item(
    business: BusinessDocument,
    title: str,
    price_minor: int | None,
    *,
    kind: KnowledgeItemKind = KnowledgeItemKind.MENU_ITEM,
    body: str | None = None,
    tags: list[str] | None = None,
    currency_code: str | None = None,
    duration_minutes: int | None = None,
    is_active: bool = True,
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=business.id,
        kind=kind,
        title=KnowledgeTitle(title),
        body=KnowledgeBody(body) if body is not None else None,
        price_minor=MoneyAmountMinor(price_minor) if price_minor is not None else None,
        currency_code=CurrencyCode(currency_code) if currency_code else None,
        duration_minutes=(
            ServiceDurationMinutes(duration_minutes)
            if duration_minutes is not None
            else None
        ),
        tags=[KnowledgeTag(tag) for tag in tags or []],
        is_active=is_active,
    )

"""The combined view of a brand: every location's value, sources and inbox."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.value import ValuePeriod
from app.schemas.dto.brands.brand_views import BrandLocationView
from app.schemas.dto.inbox.inbox_attention import InboxAttentionCounts
from app.schemas.dto.value.customer_sources import CustomerSourcesView
from app.schemas.dto.value.value_model import ValueModel
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.brands.booleans import IsLocationLocked
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.brands.strings import BrandName
from app.schemas.typings.users.prefixed_id import UserId


class BrandDashboardQuery(ImmutableDTO):
    """
    The brand's locations over one period: a named period, or local dates
    `date_from` to `date_to` (each location in its own time zone); neither:
    the last 30 days.
    """

    user_id: UserId
    brand_id: BrandId
    period: ValuePeriod | None = None
    date_from: LocalDate | None = None
    date_to: LocalDate | None = None


class BrandLocationDashboard(ImmutableDTO):
    """
    One location as the viewer may see it: the value of the period (money
    left out for a manager, as for staff), where customers came from
    (brand owners only, else None) and what waits for its team.
    `is_locked`: the location asks for a two-factor sign-in the viewer's
    session lacks, so nothing of it is shown.
    """

    location: BrandLocationView
    value: ValueModel | None = None
    sources: CustomerSourcesView | None = None
    inbox: InboxAttentionCounts | None = None
    is_locked: IsLocationLocked = False


class BrandDashboard(ImmutableDTO):
    """Every location the viewer reaches, oldest first, side by side."""

    brand_id: BrandId
    name: BrandName
    viewer_role: BrandMemberRole
    locations: list[BrandLocationDashboard] = Field(
        default_factory=list[BrandLocationDashboard]
    )

"""Where an owner's customers came from in a period (Reports)."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.value_repositories import CustomerSourceRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.customer_sources import (
    ConversationBookingCount,
    ConversationLeadCount,
    CustomerSourcesQuery,
    CustomerSourcesView,
)
from app.schemas.dto.value.value_views import BusinessValueQuery
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.use_cases.insights.value.customer_source_rows import (
    SourcePricing,
    build_source_rows,
    tally_rows,
)
from app.use_cases.insights.value.value_access import choose_value_dates, local_today
from app.use_cases.insights.value.value_estimates import (
    EstimateCatalogs,
    ValueEstimates,
    estimate_business_value,
)
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    local_day_start_microseconds,
    to_local_date,
)
from app.utilities.value.value_periods import ValueDates


class GetCustomerSourcesUseCase(
    UseCaseContract[CustomerSourcesQuery, CustomerSourcesView]
):
    """
    Conversations, kept bookings, requests and their value per customer
    source for local dates of the business (owners): the tag a link, a QR
    code, an ad or the phone line gave a conversation when it started. A
    booking counts in the period it was made, for the source of its
    conversation. Counts only, no personal data, so no audit entry.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        customer_source_repo: CustomerSourceRepoContract,
        catalogs: EstimateCatalogs,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._customer_source_repo: CustomerSourceRepoContract = customer_source_repo
        self._catalogs: EstimateCatalogs = catalogs
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CustomerSourcesQuery) -> CustomerSourcesView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        dates: ValueDates = choose_value_dates(
            BusinessValueQuery(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                period=input_data.period,
                date_from=input_data.date_from,
                date_to=input_data.date_to,
            ),
            local_today(business, self._wall_clock),
        )
        zone: ZoneInfo = load_time_zone(business.timezone)
        start: Microseconds = Microseconds(
            local_day_start_microseconds(dates.date_from, zone)
        )
        end: Microseconds = Microseconds(
            local_day_start_microseconds(dates.date_to + timedelta(days=1), zone)
        )
        repo: CustomerSourceRepoContract = self._customer_source_repo
        bookings: list[ConversationBookingCount] = repo.count_bookings_by_conversation(
            business.id, start, end
        )
        leads: list[ConversationLeadCount] = repo.count_leads_by_conversation(
            business.id, start, end
        )
        conversation_ids: list[ConversationId] = [
            *(booking.conversation_id for booking in bookings),
            *(lead.conversation_id for lead in leads),
        ]
        estimates: ValueEstimates = estimate_business_value(self._catalogs, business)
        return CustomerSourcesView(
            business_id=business.id,
            currency_code=business.currency_code,
            date_from=to_local_date(dates.date_from),
            date_to=to_local_date(dates.date_to),
            value_basis=estimates.rates.basis,
            rows=build_source_rows(
                tally_rows(
                    repo.count_conversations_by_source(business.id, start, end),
                    bookings,
                    leads,
                    repo.find_origins(business.id, conversation_ids),
                    business.currency_code,
                ),
                SourcePricing(
                    basis=estimates.rates.basis,
                    average_check=estimates.rates.average_check,
                ),
            ),
        )

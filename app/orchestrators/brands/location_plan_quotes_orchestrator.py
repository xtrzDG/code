from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.brands.location_plans import (
    LocationPlanQuery,
    LocationPlanQuoteList,
    LocationPricing,
)
from app.schemas.dto.catalog.plan_quotes import PlanQuoteList, PlanQuoteRequest
from app.utilities.brands.location_quotes import price_for_location


class LocationPlanQuotesOrchestrator(
    OrchestratorContract[LocationPlanQuery, LocationPlanQuoteList]
):
    """
    GET /v1/businesses/{business_id}/billing/plans: every plan priced as
    this business would be billed for it (the cabinet's billing page).
    How the business pays (owners only; a further location of a brand,
    a brand setup fee another location carries) comes first, then the
    country's catalog quotes, repriced for the location
    (`app/utilities/brands/location_quotes.py`).
    """

    def __init__(
        self,
        describe_pricing: UseCaseContract[LocationPlanQuery, LocationPricing],
        quote_plans: UseCaseContract[PlanQuoteRequest, PlanQuoteList],
    ) -> None:
        self._describe_pricing: UseCaseContract[LocationPlanQuery, LocationPricing] = (
            describe_pricing
        )
        self._quote_plans: UseCaseContract[PlanQuoteRequest, PlanQuoteList] = (
            quote_plans
        )

    def execute(self, input_data: LocationPlanQuery) -> LocationPlanQuoteList:
        pricing: LocationPricing = self._describe_pricing.run(input_data)
        catalog: PlanQuoteList = self._quote_plans.run(
            PlanQuoteRequest(
                country_code=pricing.country_code,
                display_language=pricing.display_language,
            )
        )
        return LocationPlanQuoteList(
            country_code=catalog.country_code,
            display_language=catalog.display_language,
            local_currency_code=catalog.local_currency_code,
            exchange_rate=catalog.exchange_rate,
            quotes=[
                price_for_location(
                    quote,
                    pricing.is_additional_location,
                    pricing.is_setup_fee_covered,
                    catalog.display_language,
                )
                for quote in catalog.quotes
            ],
            business_id=pricing.business_id,
            is_additional_location=pricing.is_additional_location,
            is_setup_fee_covered=pricing.is_setup_fee_covered,
        )

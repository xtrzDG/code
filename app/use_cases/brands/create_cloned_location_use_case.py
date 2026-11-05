from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.dto.brands.location_templates import ClonedLocationRequest
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.use_cases.brands.brand_audit import BRAND_LOCATION_ENTITY, record_in_locations
from app.utilities.analytics.product_event_drafts import business_created_event


class CreateClonedLocationUseCase(
    UseCaseContract[ClonedLocationRequest, BusinessDocument]
):
    """
    The new location itself: a business of the brand, owned by the brand
    owner who asked, with the source's settings (niche, country, time
    zone, currency, languages, plan, data region, recording retention,
    two-factor rule) and its own name and city. It starts onboarding, with
    no team but its owner, no chat address, no accepted DPA, no
    subscription and no referral: those are each business's own.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        audit_log_repo: AuditLogRepoContract,
        product_events: RecordProductEventFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._product_events: RecordProductEventFacilitatorContract = product_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ClonedLocationRequest) -> BusinessDocument:
        source: BusinessDocument = input_data.source
        now: Microseconds = self._wall_clock.now_unix()
        business = BusinessDocument(
            name=input_data.name,
            niche_key=source.niche_key,
            country_code=source.country_code,
            city=input_data.city,
            timezone=source.timezone,
            currency_code=source.currency_code,
            languages=list(source.languages),
            default_language=source.default_language,
            owner_language=source.owner_language,
            plan_key=source.plan_key,
            data_region=source.data_region,
            members=[
                BusinessMember(
                    user_id=input_data.user_id, role=BusinessMemberRole.OWNER
                )
            ],
            recording_retention_days=source.recording_retention_days,
            require_mfa_for_members=source.require_mfa_for_members,
            brand_id=input_data.brand_id,
            created_at=now,
            updated_at=now,
        )
        self._business_repo.save(business)
        record_in_locations(
            self._audit_log_repo,
            [business.id],
            input_data.user_id,
            AuditAction.CREATE,
            BRAND_LOCATION_ENTITY,
            AuditEntityReference(str(input_data.brand_id)),
            input_data.client_ip_address,
            now,
        )
        self._product_events.record(
            business_created_event(business, input_data.user_id)
        )
        return business

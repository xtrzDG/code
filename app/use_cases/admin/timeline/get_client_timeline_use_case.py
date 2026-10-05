from typed_time_provider import Microseconds

from app.contracts.repositories.analytics_repositories import ProductEventRepoContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    OnboardingRequestRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.client_care_repositories import (
    BillingCreditRepoContract,
    ClientHealthChangeRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.client_story import (
    ClientTimelineEntry,
    ClientTimelinePage,
    ClientTimelineQuery,
)
from app.schemas.dto.listing_filters import AuditLogFilter
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.timeline.timeline_lines import (
    audit_lines,
    credit_lines,
    health_lines,
    invoice_lines,
    onboarding_lines,
    product_lines,
)
from app.use_cases.admin.timeline.timeline_merge import (
    PagedLines,
    decode_before,
    merge_page,
)
from app.use_cases.shared.business_access import require_business

# A business's product steps in its life: the tunnel's screens, milestones,
# billing steps; well under this.
MAX_PRODUCT_EVENTS: DocumentQueryLimit = DocumentQueryLimit(1000)


class GetClientTimelineUseCase(
    UseCaseContract[ClientTimelineQuery, ClientTimelinePage]
):
    """
    GET /v1/admin/clients/{business_id}/timeline: the client's story, newest
    first, one page at a time: the audit log (what its team, support and the
    platform team did, with the admins' reasons; views left out), invoices
    issued, paid and failed, credit used, the subscription's steps, health
    changes, the setup's milestones and the done-for-you request, each with
    the person behind it by name. Any platform admin role reads it; it shows
    no customer's personal data, so it is not audited itself.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        business_repo: BusinessRepoContract,
        audit_log_repo: AuditLogRepoContract,
        invoice_repo: InvoiceRepoContract,
        billing_credit_repo: BillingCreditRepoContract,
        product_event_repo: ProductEventRepoContract,
        client_health_change_repo: ClientHealthChangeRepoContract,
        onboarding_request_repo: OnboardingRequestRepoContract,
        user_repo: UserRepoContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._billing_credit_repo: BillingCreditRepoContract = billing_credit_repo
        self._product_event_repo: ProductEventRepoContract = product_event_repo
        self._health_change_repo: ClientHealthChangeRepoContract = (
            client_health_change_repo
        )
        self._onboarding_request_repo: OnboardingRequestRepoContract = (
            onboarding_request_repo
        )
        self._user_repo: UserRepoContract = user_repo

    def run(self, input_data: ClientTimelineQuery) -> ClientTimelinePage:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_CLIENTS,
            )
        )
        business_id: BusinessId = require_business(
            self._business_repo, input_data.business_id
        ).id
        before: Microseconds | None = decode_before(input_data.page.cursor)
        size: int = int(input_data.page.size)
        credits: list[BillingCreditDocument] = (
            self._billing_credit_repo.list_by_business(business_id)
        )
        whole: list[ClientTimelineEntry] = [
            *invoice_lines(self._invoice_repo.list_by_business(business_id)),
            *credit_lines(credits),
            *product_lines(
                self._product_event_repo.list_by_business(
                    business_id, MAX_PRODUCT_EVENTS
                )
            ),
            *onboarding_lines(
                self._onboarding_request_repo.get_by_business(business_id)
            ),
        ]
        page: ClientTimelinePage = merge_page(
            whole,
            [
                self._audit_page(business_id, credits, before, size),
                self._health_page(business_id, before, size),
            ],
            before,
            size,
        )
        return page.model_copy(update={"items": self._named(page.items)})

    def _audit_page(
        self,
        business_id: BusinessId,
        credits: list[BillingCreditDocument],
        before: Microseconds | None,
        size: int,
    ) -> PagedLines:
        entries = self._audit_log_repo.page_by_business(
            business_id,
            KeysetSlice(limit=KeysetReadLimit(size)),
            AuditLogFilter(until=before),
        )
        return PagedLines(
            lines=audit_lines(entries, credits),
            oldest=min((entry.created_at for entry in entries), key=int, default=None),
            is_full=len(entries) >= size,
        )

    def _health_page(
        self, business_id: BusinessId, before: Microseconds | None, size: int
    ) -> PagedLines:
        changes = self._health_change_repo.list_before(
            business_id, before, DocumentQueryLimit(size)
        )
        return PagedLines(
            lines=health_lines(changes),
            oldest=min(
                (change.changed_at for change in changes), key=int, default=None
            ),
            is_full=len(changes) >= size,
        )

    def _named(self, lines: list[ClientTimelineEntry]) -> list[ClientTimelineEntry]:
        """Each line with its person's name, read in one go."""

        people: list[UserId] = sorted(
            {line.actor_user_id for line in lines if line.actor_user_id is not None},
            key=str,
        )
        names = {
            user.id: user.display_name for user in self._user_repo.get_many(people)
        }
        return [
            line
            if line.actor_user_id is None
            else line.model_copy(update={"actor_name": names.get(line.actor_user_id)})
            for line in lines
        ]

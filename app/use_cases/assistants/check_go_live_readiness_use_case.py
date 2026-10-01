from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories import (
    BusinessProfileRepoContract,
    DpaAcceptanceRepoContract,
    KnowledgeItemRepoContract,
    ResourceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.profiles import ProfileGapFinding
from app.schemas.exceptions.application_errors import ConflictError
from app.use_cases.billing.billing_records import (
    find_current_subscription,
    is_service_paid_for,
)
from app.utilities.knowledge.profile_gaps import find_profile_gaps


class CheckGoLiveReadinessUseCase(UseCaseContract[BusinessDocument, None]):
    """
    Refuse to make an assistant live while a launch condition is missing
    (concept: the trial or a paid subscription, the data processing
    agreement, and section 4 "Проверка" - nothing blocking left in the
    profile, including a staff contact that receives handoffs, bookings and
    leads).

    Raises:
        ConflictError: listing everything still missing.
    """

    def __init__(
        self,
        subscription_repo: SubscriptionRepoContract,
        dpa_acceptance_repo: DpaAcceptanceRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._dpa_acceptance_repo: DpaAcceptanceRepoContract = dpa_acceptance_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BusinessDocument) -> None:
        business: BusinessDocument = input_data
        missing: list[str] = []
        if not is_service_paid_for(
            find_current_subscription(self._subscription_repo, business.id),
            self._wall_clock.now_unix(),
        ):
            missing.append("start the trial or pay for the subscription")

        if not self._is_dpa_accepted(business):
            missing.append(
                "accept the data processing agreement (version "
                f"{self._app_settings.dpa_document_version})"
            )

        blocking: list[ProfileGapFinding] = [
            finding
            for finding in find_profile_gaps(
                template=self._niche_template_registry.get(business.niche_key),
                business=business,
                profile=self._business_profile_repo.get_by_business(business.id),
                knowledge_items=self._knowledge_item_repo.list_by_business(business.id),
                resources=self._resource_repo.list_by_business(business.id),
            )
            if finding.is_blocking
        ]
        if blocking:
            kinds: list[str] = list(
                dict.fromkeys(finding.kind.value for finding in blocking)
            )
            missing.append(
                "complete the profile (see what to add: " + ", ".join(kinds) + ")"
            )

        if missing:
            raise ConflictError(
                "The assistant cannot go live yet: " + "; ".join(missing) + "."
            )

    def _is_dpa_accepted(self, business: BusinessDocument) -> bool:
        return any(
            acceptance.document_version == self._app_settings.dpa_document_version
            for acceptance in self._dpa_acceptance_repo.list_by_business(business.id)
        )

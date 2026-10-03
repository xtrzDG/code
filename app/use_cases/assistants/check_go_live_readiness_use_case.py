"""Whether a version of the assistant may go live, check by check."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import (
    NicheTemplateRegistryContract,
    PlanRegistryContract,
)
from app.contracts.repositories.assistant_repositories import AutotestRunRepoContract
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import BusinessProfileRepoContract
from app.contracts.repositories.compliance_repositories import DpaAcceptanceRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import VoiceAgentProvisionerAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import GoLiveCheckCode
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.go_live import (
    GoLiveCheck,
    GoLiveReadiness,
    GoLiveReadinessRequest,
)
from app.schemas.dto.profiles.profile_gaps import ProfileGapFinding
from app.schemas.typings.assistants.constrained_strings import GoLiveCheckDetail
from app.schemas.typings.assistants.strings import GoLiveCheckMessage
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.use_cases.assistants.go_live_autotest_checks import (
    check_autotests,
    summarize_autotest_run,
)
from app.use_cases.billing.billing_records import (
    find_current_subscription,
    is_service_paid_for,
)
from app.use_cases.billing.trial_subscriptions import (
    choose_go_live_trial,
    is_trial_due_at_go_live,
)
from app.utilities.knowledge.profile_gaps import find_profile_gaps

NO_SUBSCRIPTION_DETAIL: str = "none"
# The detail of a gate passed because the free trial starts at go-live.
TRIAL_AT_GO_LIVE_DETAIL: str = "trial_at_go_live"
APP_BASE_URL_SETTING: str = "APP_BASE_URL"


class CheckGoLiveReadinessUseCase(
    UseCaseContract[GoLiveReadinessRequest, GoLiveReadiness]
):
    """
    The go-live checklist of a version (concept: the trial or a paid
    subscription, the data processing agreement, and section 4 "Проверка" -
    nothing blocking left in the profile, a staff contact that receives
    handoffs, bookings and leads, passed autotests, and for voice versions
    a voice platform the server can set agents up on).

    It only reports; publishing and rollback refuse with the failed blocking
    checks as reasons. Voice settings missing in development or test are a
    warning: such a version goes live without a voice agent there.
    """

    def __init__(
        self,
        subscription_repo: SubscriptionRepoContract,
        dpa_acceptance_repo: DpaAcceptanceRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        plan_registry: PlanRegistryContract,
        voice_agent_provisioner: VoiceAgentProvisionerAdapterContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._dpa_acceptance_repo: DpaAcceptanceRepoContract = dpa_acceptance_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._plan_registry: PlanRegistryContract = plan_registry
        self._voice_agent_provisioner: VoiceAgentProvisionerAdapterContract = (
            voice_agent_provisioner
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: GoLiveReadinessRequest) -> GoLiveReadiness:
        business: BusinessDocument = input_data.business
        version: AssistantVersionDocument = input_data.version
        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo, business.id
        )
        run: AutotestRunDocument | None = (
            self._autotest_run_repo.get(business.id, version.autotest_run_id)
            if version.autotest_run_id is not None
            else None
        )
        checks: list[GoLiveCheck] = [
            self._check_subscription(business, subscription),
            self._check_dpa(business),
            *self._check_profile(business),
            check_autotests(version, run),
        ]
        if version.is_voice_enabled:
            checks.append(self._check_voice_configuration())

        return GoLiveReadiness(
            business_id=business.id,
            assistant_version_id=version.id,
            version_number=version.version_number,
            version_status=version.status,
            is_ready=all(check.is_ok or not check.is_blocking for check in checks),
            checks=checks,
            autotest_run=None if run is None else summarize_autotest_run(run),
            subscription_status=None if subscription is None else subscription.status,
            dpa_document_version=self._app_settings.dpa_document_version,
        )

    def _check_subscription(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument | None,
    ) -> GoLiveCheck:
        is_paid: bool = is_service_paid_for(subscription, self._wall_clock.now_unix())
        plan_key, _ = choose_go_live_trial(business, subscription)
        is_trial_due: bool = not is_paid and is_trial_due_at_go_live(
            self._subscription_repo.list_by_business(business.id),
            self._plan_registry.get(plan_key),
        )
        message: str = "Pay for the subscription to go live."
        detail: str = (
            NO_SUBSCRIPTION_DETAIL
            if subscription is None
            else subscription.status.value
        )
        if is_paid:
            message = "The trial or a paid subscription covers the assistant."
        elif is_trial_due:
            message = "The free trial starts when the assistant goes live."
            detail = TRIAL_AT_GO_LIVE_DETAIL

        return GoLiveCheck(
            code=GoLiveCheckCode.SUBSCRIPTION_OR_TRIAL,
            is_ok=is_paid or is_trial_due,
            is_blocking=True,
            message=GoLiveCheckMessage(message),
            details=[GoLiveCheckDetail(detail)],
        )

    def _check_dpa(self, business: BusinessDocument) -> GoLiveCheck:
        version: str = str(self._app_settings.dpa_document_version)
        is_accepted: bool = any(
            str(acceptance.document_version) == version
            for acceptance in self._dpa_acceptance_repo.list_by_business(business.id)
        )
        return GoLiveCheck(
            code=GoLiveCheckCode.DPA,
            is_ok=is_accepted,
            is_blocking=True,
            message=GoLiveCheckMessage(
                f"The data processing agreement (version {version}) is accepted."
                if is_accepted
                else f"Accept the data processing agreement (version {version})."
            ),
            details=[GoLiveCheckDetail(version)],
        )

    def _check_profile(self, business: BusinessDocument) -> list[GoLiveCheck]:
        """Blocking profile gaps, with the missing staff contact on its own."""

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
        has_staff_contact: bool = not any(
            finding.kind is ProfileGapKind.NO_HANDOFF_CONTACT for finding in blocking
        )
        gap_kinds: list[str] = list(
            dict.fromkeys(
                finding.kind.value
                for finding in blocking
                if finding.kind is not ProfileGapKind.NO_HANDOFF_CONTACT
            )
        )
        return [
            GoLiveCheck(
                code=GoLiveCheckCode.PROFILE_GAPS,
                is_ok=gap_kinds == [],
                is_blocking=True,
                message=GoLiveCheckMessage(
                    "Nothing required is missing in the profile."
                    if gap_kinds == []
                    else "Complete the profile (see what to add: "
                    + ", ".join(gap_kinds)
                    + ")."
                ),
                details=[GoLiveCheckDetail(kind) for kind in gap_kinds],
            ),
            GoLiveCheck(
                code=GoLiveCheckCode.STAFF_CONTACT,
                is_ok=has_staff_contact,
                is_blocking=True,
                message=GoLiveCheckMessage(
                    "A staff contact receives handoffs, bookings and leads."
                    if has_staff_contact
                    else "Add a staff contact who receives handoffs, bookings "
                    "and leads."
                ),
                details=(
                    []
                    if has_staff_contact
                    else [GoLiveCheckDetail(ProfileGapKind.NO_HANDOFF_CONTACT.value)]
                ),
            ),
        ]

    def _check_voice_configuration(self) -> GoLiveCheck:
        missing: list[EnvironmentVariableName] = []
        if self._app_settings.app_base_url is None:
            missing.append(EnvironmentVariableName(APP_BASE_URL_SETTING))

        missing.extend(self._voice_agent_provisioner.list_missing_settings())
        if missing == []:
            return GoLiveCheck(
                code=GoLiveCheckCode.VOICE_CONFIGURATION,
                is_ok=True,
                is_blocking=True,
                message=GoLiveCheckMessage("The voice agent can be set up."),
            )

        names: str = ", ".join(str(name) for name in missing)
        is_production: bool = (
            self._app_settings.environment is DeploymentEnvironment.PRODUCTION
        )
        return GoLiveCheck(
            code=GoLiveCheckCode.VOICE_CONFIGURATION,
            is_ok=False,
            is_blocking=is_production,
            message=GoLiveCheckMessage(
                f"The voice agent cannot be set up: {names} is not configured."
                if is_production
                else f"Voice is not configured on this server ({names}); the "
                "version goes live without a voice agent (development only)."
            ),
            details=[GoLiveCheckDetail(str(name)) for name in missing],
        )

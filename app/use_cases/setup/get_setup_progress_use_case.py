from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import NicheTemplateRegistryContract, PlanRegistryContract
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.compliance_repositories import DpaAcceptanceRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.repositories.setup_repositories import (
    ActivationEventRepoContract,
    SetupStateRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.setup import (
    ActivationEventKind,
    SetupActionTarget,
    SetupStepStatus,
)
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import ActivationEventDocument, SetupStateDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.apply_changes import (
    ApplyChangesSource,
    ApplyChangesView,
    SetupActionView,
)
from app.schemas.dto.setup.setup_progress import (
    ActivationMilestoneCheck,
    SetupQuery,
    SetupView,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.setup.constrained_integers import (
    SetupMinutesLeft,
    SetupPercent,
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
from app.utilities.setup.setup_steps import (
    SetupFacts,
    StepState,
    assign_statuses,
    can_go_live,
    compute_minutes_left,
    compute_percent,
    derive_steps,
)
from app.utilities.setup.setup_texts import APPLY_CHANGES_AGAIN_LABEL
from app.utilities.setup.setup_views import (
    action_view,
    milestone_views,
    phone_test_links,
    step_views,
)

TRY_SIGNALS: frozenset[ActivationEventKind] = frozenset(
    {ActivationEventKind.TEST_CHAT_TRIED, ActivationEventKind.FIRST_CONVERSATION}
)


class GetSetupProgressUseCase(UseCaseContract[SetupQuery, SetupView]):
    """
    The guided setup of a business, derived from what it already has: the
    seven steps in order (business, offer, hours and bookings, staff
    contact, channels, test, launch), each done, skipped, next or to do with
    what it misses and where to fix it; the share done and the minutes
    left; links to try the assistant from a phone; the milestones reached
    (noticed and stored first); and "Apply changes" progress. Owners and
    staff may read it; texts are in the owner's language by default.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        record_activation_milestones: UseCaseContract[ActivationMilestoneCheck, None],
        describe_apply_changes: UseCaseContract[ApplyChangesSource, ApplyChangesView],
        business_profile_repo: BusinessProfileRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        resource_repo: ResourceRepoContract,
        channel_repo: ChannelRepoContract,
        subscription_repo: SubscriptionRepoContract,
        dpa_acceptance_repo: DpaAcceptanceRepoContract,
        activation_event_repo: ActivationEventRepoContract,
        setup_state_repo: SetupStateRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        plan_registry: PlanRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize: UseCaseContract[BusinessAccessRequest, BusinessDocument] = (
            authorize_business_access
        )
        self._record_activation_milestones: UseCaseContract[
            ActivationMilestoneCheck, None
        ] = record_activation_milestones
        self._describe_apply_changes: UseCaseContract[
            ApplyChangesSource, ApplyChangesView
        ] = describe_apply_changes
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._dpa_acceptance_repo: DpaAcceptanceRepoContract = dpa_acceptance_repo
        self._activation_event_repo: ActivationEventRepoContract = activation_event_repo
        self._setup_state_repo: SetupStateRepoContract = setup_state_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._plan_registry: PlanRegistryContract = plan_registry
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SetupQuery) -> SetupView:
        business: BusinessDocument = self._authorize.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        language: LanguageTag = input_data.language or business.owner_language
        self._record_activation_milestones.run(
            ActivationMilestoneCheck(business_id=business.id)
        )
        events: list[ActivationEventDocument] = (
            self._activation_event_repo.list_by_business(business.id)
        )
        state: SetupStateDocument | None = self._setup_state_repo.get_by_business(
            business.id
        )
        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo, business.id
        )
        is_live: bool = business.published_assistant_version_id is not None
        facts = SetupFacts(
            findings=find_profile_gaps(
                template=self._niche_template_registry.get(business.niche_key),
                business=business,
                profile=self._business_profile_repo.get_by_business(business.id),
                knowledge_items=self._knowledge_item_repo.list_by_business(business.id),
                resources=self._resource_repo.list_by_business(business.id),
            ),
            has_staff_contact=business.manager_contacts != [],
            has_connected_channel=any(
                channel.status is ChannelStatus.CONNECTED
                and channel.kind is not ChannelKind.OWNER_TEST
                for channel in self._channel_repo.list_by_business(business.id)
            ),
            has_tried_assistant=any(event.kind in TRY_SIGNALS for event in events),
            is_live=is_live,
            is_agreement_accepted=self._is_agreement_accepted(business),
            is_service_available=self._is_service_available(business, subscription),
            skipped=frozenset(() if state is None else state.skipped_steps),
        )
        steps: list[StepState] = derive_steps(facts)
        statuses: list[SetupStepStatus] = assign_statuses(steps, facts.skipped)
        apply: ApplyChangesView = self._describe_apply_changes.run(
            ApplyChangesSource(business=business, language=language)
        )
        next_step: StepState | None = next(
            (
                step
                for step, status in zip(steps, statuses, strict=True)
                if status is SetupStepStatus.NEXT
            ),
            None,
        )
        return SetupView(
            business_id=business.id,
            language=language,
            steps=step_views(steps, statuses, language, self._resolver),
            next_step=None if next_step is None else next_step.code,
            next_action=self._next_action(next_step, apply, is_live, language),
            percent=SetupPercent(compute_percent(statuses)),
            minutes_left=SetupMinutesLeft(compute_minutes_left(steps, statuses)),
            can_go_live=can_go_live(steps, facts),
            is_live=is_live,
            is_complete=all(step.is_done for step in steps if step.is_required),
            went_live_at=next(
                (
                    event.occurred_at
                    for event in events
                    if event.kind is ActivationEventKind.WENT_LIVE
                ),
                None,
            ),
            trial_ends_at=(
                subscription.trial_ends_at
                if subscription is not None
                and subscription.status is SubscriptionStatus.TRIALING
                else None
            ),
            phone_test_links=phone_test_links(
                business,
                self._channel_repo.list_by_business(business.id),
                self._app_settings.app_base_url,
                is_live,
            ),
            milestones=milestone_views(events),
            apply=apply,
        )

    def _next_action(
        self,
        next_step: StepState | None,
        apply: ApplyChangesView,
        is_live: bool,
        language: LanguageTag,
    ) -> SetupActionView:
        # Once live, changes customers do not get yet come before the
        # optional steps still open.
        if is_live and apply.has_unapplied_changes and not apply.is_in_progress:
            return action_view(
                SetupActionTarget.APPLY_CHANGES,
                language,
                self._resolver,
                label=APPLY_CHANGES_AGAIN_LABEL,
            )

        if next_step is not None:
            return action_view(
                next_step.target, language, self._resolver, next_step.profile_step
            )

        return action_view(SetupActionTarget.OVERVIEW, language, self._resolver)

    def _is_agreement_accepted(self, business: BusinessDocument) -> bool:
        version: str = str(self._app_settings.dpa_document_version)
        return any(
            str(acceptance.document_version) == version
            for acceptance in self._dpa_acceptance_repo.list_by_business(business.id)
        )

    def _is_service_available(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument | None,
    ) -> bool:
        if is_service_paid_for(subscription, self._wall_clock.now_unix()):
            return True

        plan_key, _ = choose_go_live_trial(business, subscription)
        return is_trial_due_at_go_live(
            self._subscription_repo.list_by_business(business.id),
            self._plan_registry.get(plan_key),
        )

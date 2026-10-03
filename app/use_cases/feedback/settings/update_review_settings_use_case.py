from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.feedback_repositories import (
    ReviewSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.feedback import ReviewSettingsDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.feedback.review_settings import (
    ReviewSettingsView,
    UpdateReviewSettingsCommand,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.feedback.settings.review_settings_views import (
    build_review_settings_view,
    stored_or_default,
)
from app.utilities.setup.profile_patching import next_revision_time

REVIEW_SETTINGS_ENTITY: AuditEntityName = AuditEntityName("review_settings")


class UpdateReviewSettingsUseCase(
    UseCaseContract[UpdateReviewSettingsCommand, ReviewSettingsView]
):
    """
    The owner turns feedback after visits on or off, sets the delay after
    a visit, names the approved WhatsApp template and the Google review
    page. The link is the profile's link of kind `google_review` (the
    assistant may send it too), changed in one step with the stored
    profile. Feedback can be on without a review link: customers are then
    thanked without the invitation. Audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        review_settings_repo: ReviewSettingsRepoContract,
        profile_repo: BusinessProfileRepoContract,
        channel_repo: ChannelRepoContract,
        audit_log_repo: AuditLogRepoContract,
        text_resolver: LocalizedTextResolverContract,
        wall_clock: WallClock[Microseconds],
        app_base_url: PublicBaseUrl | None,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._review_settings_repo: ReviewSettingsRepoContract = review_settings_repo
        self._profile_repo: BusinessProfileRepoContract = profile_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._app_base_url: PublicBaseUrl | None = app_base_url

    def run(self, input_data: UpdateReviewSettingsCommand) -> ReviewSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        request = input_data.request
        profile: BusinessProfileDocument | None = self._store_review_link(
            business, request.google_review_url, now
        )
        settings: ReviewSettingsDocument = stored_or_default(
            business, self._review_settings_repo.get_by_business(business.id)
        )
        settings.is_feedback_enabled = request.is_feedback_enabled
        settings.delay_minutes = request.delay_minutes
        settings.feedback_template_name = request.feedback_template_name
        settings.updated_at = now
        self._review_settings_repo.save(settings)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.UPDATE,
                entity=REVIEW_SETTINGS_ENTITY,
                entity_id=AuditEntityReference(str(settings.id)),
                created_at=now,
                updated_at=now,
            )
        )
        return build_review_settings_view(
            business,
            settings,
            profile,
            self._channel_repo,
            self._text_resolver,
            self._app_base_url,
        )

    def _store_review_link(
        self,
        business: BusinessDocument,
        review_url: WebLink | None,
        now: Microseconds,
    ) -> BusinessProfileDocument | None:
        """The profile with the link as asked (unchanged when it already is)."""

        current: BusinessProfileDocument | None = self._profile_repo.get_by_business(
            business.id
        )
        if current is None:
            if review_url is None:
                return None

            raise ValidationFailedError(
                "Fill in the business profile before adding the review link."
            )

        if current.google_review_url == review_url:
            return current

        def change(profile: BusinessProfileDocument) -> BusinessProfileDocument:
            profile.google_review_url = review_url
            # The profile's save time is its revision (the cabinet's editors
            # see a newer one).
            profile.updated_at = next_revision_time(now, profile.updated_at)
            return profile

        return self._profile_repo.modify(business.id, change) or current

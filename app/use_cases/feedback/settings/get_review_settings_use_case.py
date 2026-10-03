from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    ReviewSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.feedback.review_settings import (
    ReviewSettingsQuery,
    ReviewSettingsView,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.use_cases.feedback.settings.review_settings_views import (
    build_review_settings_view,
    stored_or_default,
)


class GetReviewSettingsUseCase(
    UseCaseContract[ReviewSettingsQuery, ReviewSettingsView]
):
    """
    Settings → Reviews for the owner: feedback after visits on or off, the
    delay, the WhatsApp template's name, the Google review link, whether
    the WhatsApp number is connected and link visits can be counted, and
    the request to register as the template in each business language.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        review_settings_repo: ReviewSettingsRepoContract,
        profile_repo: BusinessProfileRepoContract,
        channel_repo: ChannelRepoContract,
        text_resolver: LocalizedTextResolverContract,
        app_base_url: PublicBaseUrl | None,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._review_settings_repo: ReviewSettingsRepoContract = review_settings_repo
        self._profile_repo: BusinessProfileRepoContract = profile_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._app_base_url: PublicBaseUrl | None = app_base_url

    def run(self, input_data: ReviewSettingsQuery) -> ReviewSettingsView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return build_review_settings_view(
            business,
            stored_or_default(
                business, self._review_settings_repo.get_by_business(business.id)
            ),
            self._profile_repo.get_by_business(business.id),
            self._channel_repo,
            self._text_resolver,
            self._app_base_url,
        )

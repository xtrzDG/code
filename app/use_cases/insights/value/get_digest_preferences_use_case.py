from app.contracts.repositories.notification_repositories import (
    PushSubscriptionRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.repositories.value_repositories import (
    DigestPreferencesRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.value_views import (
    DigestPreferencesQuery,
    DigestPreferencesView,
)
from app.use_cases.insights.value.value_settings_views import (
    build_digest_preferences_view,
    stored_preferences_or_default,
)


class GetDigestPreferencesUseCase(
    UseCaseContract[DigestPreferencesQuery, DigestPreferencesView]
):
    """
    Which summaries the signed-in owner gets and where they reach them
    (their sign-in e-mail, their devices with notifications on).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        digest_preferences_repo: DigestPreferencesRepoContract,
        user_repo: UserRepoContract,
        push_subscription_repo: PushSubscriptionRepoContract,
        app_settings: AppSettings,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._digest_preferences_repo: DigestPreferencesRepoContract = (
            digest_preferences_repo
        )
        self._user_repo: UserRepoContract = user_repo
        self._push_subscription_repo: PushSubscriptionRepoContract = (
            push_subscription_repo
        )
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: DigestPreferencesQuery) -> DigestPreferencesView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        return build_digest_preferences_view(
            business,
            stored_preferences_or_default(
                business,
                input_data.user_id,
                self._digest_preferences_repo.get(business.id, input_data.user_id),
            ),
            self._user_repo,
            self._push_subscription_repo,
            self._app_settings,
        )
